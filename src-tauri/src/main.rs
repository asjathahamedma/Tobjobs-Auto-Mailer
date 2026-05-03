#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use serde::Serialize;
use serde_json::{json, Value};
use std::{
    fs,
    io::{BufRead, BufReader, Write},
    os::windows::process::CommandExt,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::{SystemTime, UNIX_EPOCH},
};
use tauri::{AppHandle, Emitter, State};

const CREATE_NO_WINDOW: u32 = 0x08000000;

#[derive(Default)]
struct WorkflowState {
    pid: Arc<Mutex<Option<u32>>>,
}

#[derive(Serialize)]
struct WorkflowStatus {
    running: bool,
    pid: Option<u32>,
}

#[derive(Serialize)]
struct LaunchContext {
    startup: bool,
}

fn current_executable() -> Option<PathBuf> {
    std::env::current_exe().ok()
}

fn locate_resource_root() -> Result<PathBuf, String> {
    if let Ok(root) = std::env::var("TOPJOBS_RESOURCE_DIR") {
        let path = PathBuf::from(root);
        if path.join("run_automation.py").exists() {
            return Ok(path);
        }
    }

    let candidates = [
        std::env::current_dir().ok(),
        current_executable().and_then(|exe| exe.parent().map(|path| path.to_path_buf())),
    ];

    for candidate in candidates.iter().flatten() {
        for ancestor in candidate.ancestors() {
            if ancestor.join("run_automation.py").exists() {
                return Ok(ancestor.to_path_buf());
            }
        }
    }

    if let Some(exe) = current_executable() {
        for candidate in [
            exe.parent().map(|path| path.join("_up_")),
            exe.parent().map(|path| path.join("resources")),
            exe.parent()
                .and_then(|path| path.parent().map(|parent| parent.join("resources"))),
            exe.parent().map(|path| path.to_path_buf()),
        ]
        .into_iter()
        .flatten()
        {
            if candidate.join("run_automation.py").exists() {
                return Ok(candidate);
            }
        }
    }

    Err("Could not locate the TopJobs Auto Mailer resource root.".into())
}

fn is_local_project_root(path: &Path) -> bool {
    path.join(".git").exists() || path.join("src-tauri").exists()
}

fn locate_app_home() -> Result<PathBuf, String> {
    if let Ok(home) = std::env::var("TOPJOBS_APP_HOME") {
        return Ok(PathBuf::from(home));
    }

    let resource_root = locate_resource_root()?;
    if is_local_project_root(&resource_root) {
        return Ok(resource_root);
    }

    if let Ok(appdata) = std::env::var("APPDATA") {
        return Ok(PathBuf::from(appdata).join("TopJobs Auto Mailer"));
    }

    Ok(resource_root)
}

fn locate_install_dir(resource_root: &Path) -> PathBuf {
    if is_local_project_root(resource_root) {
        return resource_root.to_path_buf();
    }

    current_executable()
        .and_then(|exe| exe.parent().map(|path| path.to_path_buf()))
        .unwrap_or_else(|| resource_root.to_path_buf())
}

fn resolve_python(resource_root: &Path) -> String {
    let venv_python = resource_root.join(".venv").join("Scripts").join("python.exe");
    if venv_python.exists() {
        venv_python.to_string_lossy().to_string()
    } else {
        "python".to_string()
    }
}

fn configure_python_command(command: &mut Command) -> Result<(), String> {
    let resource_root = locate_resource_root()?;
    let app_home = locate_app_home()?;
    let install_dir = locate_install_dir(&resource_root);
    let executable = current_executable().unwrap_or_else(|| install_dir.join("topjobs-auto-mailer-shell.exe"));

    fs::create_dir_all(app_home.join("data")).map_err(|error| error.to_string())?;
    fs::create_dir_all(app_home.join("logs")).map_err(|error| error.to_string())?;
    fs::create_dir_all(app_home.join("resumes")).map_err(|error| error.to_string())?;

    let existing_python_path = std::env::var("PYTHONPATH").ok();
    let merged_python_path = match existing_python_path {
        Some(value) if !value.trim().is_empty() => {
            format!("{};{}", resource_root.to_string_lossy(), value)
        }
        _ => resource_root.to_string_lossy().to_string(),
    };

    command.current_dir(&app_home);
    command.env("TOPJOBS_RESOURCE_DIR", &resource_root);
    command.env("TOPJOBS_APP_HOME", &app_home);
    command.env("TOPJOBS_INSTALL_DIR", &install_dir);
    command.env("TOPJOBS_APP_EXE", &executable);
    command.env("PYTHONPATH", merged_python_path);
    command.creation_flags(CREATE_NO_WINDOW);
    Ok(())
}

fn run_python_json(args: &[&str], stdin_json: Option<String>) -> Result<Value, String> {
    let resource_root = locate_resource_root()?;
    let python = resolve_python(&resource_root);

    let mut command = Command::new(python);
    configure_python_command(&mut command)?;
    command.args(args);
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());
    if stdin_json.is_some() {
        command.stdin(Stdio::piped());
    }

    let mut child = command.spawn().map_err(|error| error.to_string())?;
    if let Some(payload) = stdin_json {
        if let Some(mut stdin) = child.stdin.take() {
            stdin
                .write_all(payload.as_bytes())
                .map_err(|error| error.to_string())?;
        }
    }

    let output = child.wait_with_output().map_err(|error| error.to_string())?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }

    serde_json::from_slice::<Value>(&output.stdout)
        .map_err(|error| format!("Failed to decode Python bridge JSON: {error}"))
}

fn emit_event(app: &AppHandle, kind: &str, payload: Value) {
    let _ = app.emit("workflow:event", json!({ "kind": kind, "payload": payload }));
}

fn emit_stream(app: &AppHandle, kind: &str, line: &str) {
    if let Ok(parsed) = serde_json::from_str::<Value>(line) {
        if let Some(parsed_kind) = parsed
            .get("type")
            .and_then(Value::as_str)
            .map(str::to_owned)
        {
            emit_event(app, &parsed_kind, parsed);
            return;
        }
    }

    emit_event(
        app,
        kind,
        json!({
            "type": kind,
            "message": line
        }),
    );
}

fn sanitize_file_name(file_name: &str) -> String {
    let filtered: String = file_name
        .chars()
        .map(|ch| match ch {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '.' | '_' | '-' | ' ' => ch,
            _ => '_',
        })
        .collect();
    filtered.trim().to_string()
}

fn store_uploaded_resume(file_name: &str, content_base64: &str) -> Result<String, String> {
    let app_home = locate_app_home()?;
    let resumes_dir = app_home.join("resumes");
    fs::create_dir_all(&resumes_dir).map_err(|error| error.to_string())?;

    let sanitized_name = sanitize_file_name(file_name);
    if sanitized_name.is_empty() || !sanitized_name.to_lowercase().ends_with(".pdf") {
        return Err("Please import a valid PDF resume.".into());
    }

    let destination = resumes_dir.join(&sanitized_name);
    let bytes = BASE64
        .decode(content_base64.as_bytes())
        .map_err(|error| format!("Could not decode resume data: {error}"))?;
    fs::write(&destination, bytes).map_err(|error| error.to_string())?;

    Ok(format!("resumes\\{}", sanitized_name))
}

fn store_temp_resume(file_name: &str, content_base64: &str) -> Result<PathBuf, String> {
    let app_home = locate_app_home()?;
    let temp_dir = app_home.join("data").join("temp_resume_drafts");
    fs::create_dir_all(&temp_dir).map_err(|error| error.to_string())?;

    let sanitized_name = sanitize_file_name(file_name);
    if sanitized_name.is_empty() || !sanitized_name.to_lowercase().ends_with(".pdf") {
        return Err("Please import a valid PDF resume.".into());
    }

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_millis();
    let temp_path = temp_dir.join(format!("{timestamp}_{sanitized_name}"));
    let bytes = BASE64
        .decode(content_base64.as_bytes())
        .map_err(|error| format!("Could not decode resume data: {error}"))?;
    fs::write(&temp_path, bytes).map_err(|error| error.to_string())?;
    Ok(temp_path)
}

#[tauri::command]
fn get_snapshot(window_days: Option<u32>) -> Result<Value, String> {
    run_python_json(
        &[
            "-m",
            "tauri_bridge.cli",
            "snapshot",
            "--days",
            &window_days.unwrap_or(30).to_string(),
        ],
        None,
    )
}

#[tauri::command]
fn get_config() -> Result<Value, String> {
    run_python_json(&["-m", "tauri_bridge.cli", "config-get"], None)
}

#[tauri::command]
fn save_config(config: Value) -> Result<Value, String> {
    run_python_json(
        &["-m", "tauri_bridge.cli", "config-save"],
        Some(config.to_string()),
    )
}

#[tauri::command]
fn get_resume_inventory() -> Result<Value, String> {
    run_python_json(&["-m", "tauri_bridge.cli", "resume-inventory"], None)
}

#[tauri::command]
fn import_resume(file_name: String, content_base64: String) -> Result<Value, String> {
    let relative_resume_path = store_uploaded_resume(&file_name, &content_base64)?;

    run_python_json(
        &[
            "-m",
            "tauri_bridge.cli",
            "resume-import",
            "--path",
            &relative_resume_path,
        ],
        None,
    )
}

#[tauri::command]
fn analyze_resume_profile(file_name: String, content_base64: String) -> Result<Value, String> {
    let temp_resume_path = store_temp_resume(&file_name, &content_base64)?;
    let temp_path_arg = temp_resume_path.to_string_lossy().to_string();
    let result = run_python_json(
        &[
            "-m",
            "tauri_bridge.cli",
            "resume-profile-draft",
            "--path",
            &temp_path_arg,
        ],
        None,
    );
    let _ = fs::remove_file(&temp_resume_path);
    result
}

#[tauri::command]
fn create_resume_profile(
    file_name: String,
    content_base64: String,
    profile: Value,
) -> Result<Value, String> {
    let relative_resume_path = store_uploaded_resume(&file_name, &content_base64)?;
    run_python_json(
        &[
            "-m",
            "tauri_bridge.cli",
            "resume-profile-create",
            "--path",
            &relative_resume_path,
        ],
        Some(profile.to_string()),
    )
}

#[tauri::command]
fn get_workflow_status(state: State<'_, WorkflowState>) -> WorkflowStatus {
    let pid = *state.pid.lock().expect("workflow state poisoned");
    WorkflowStatus {
        running: pid.is_some(),
        pid,
    }
}

#[tauri::command]
fn get_launch_context() -> LaunchContext {
    LaunchContext {
        startup: std::env::args().any(|arg| arg == "--startup"),
    }
}

#[tauri::command]
fn start_workflow(
    app: AppHandle,
    state: State<'_, WorkflowState>,
    startup: Option<bool>,
) -> Result<(), String> {
    {
        let guard = state.pid.lock().map_err(|_| "Workflow state unavailable.")?;
        if guard.is_some() {
            return Err("Workflow is already running.".into());
        }
    }

    let resource_root = locate_resource_root()?;
    let python = resolve_python(&resource_root);
    let mut command = Command::new(python);
    configure_python_command(&mut command)?;
    command.args(["-u", "-m", "tauri_bridge.workflow_runner"]);
    if startup.unwrap_or(false) {
        command.arg("--startup");
    }
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    let mut child = command.spawn().map_err(|error| error.to_string())?;
    let pid = child.id();
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Failed to capture workflow stdout.".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "Failed to capture workflow stderr.".to_string())?;

    {
        let mut guard = state.pid.lock().map_err(|_| "Workflow state unavailable.")?;
        *guard = Some(pid);
    }

    let pid_state = state.inner().pid.clone();
    let stdout_app = app.clone();
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().map_while(Result::ok) {
            emit_stream(&stdout_app, "log", &line);
        }
    });

    let stderr_app = app.clone();
    thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines().map_while(Result::ok) {
            emit_stream(&stderr_app, "stderr", &line);
        }
    });

    let finish_app = app.clone();
    thread::spawn(move || {
        let status = child.wait();
        if let Ok(mut guard) = pid_state.lock() {
            *guard = None;
        }

        match status {
            Ok(exit_status) => {
                emit_event(
                    &finish_app,
                    "process-exit",
                    json!({
                        "type": "process-exit",
                        "success": exit_status.success(),
                        "code": exit_status.code(),
                    }),
                );
            }
            Err(error) => {
                emit_event(
                    &finish_app,
                    "error",
                    json!({
                        "type": "error",
                        "message": error.to_string(),
                    }),
                );
            }
        }
    });

    emit_event(
        &app,
        "state",
        json!({
            "type": "state",
            "status": "started",
            "pid": pid
        }),
    );

    Ok(())
}

#[tauri::command]
fn stop_workflow(state: State<'_, WorkflowState>) -> Result<(), String> {
    let pid = {
        let guard = state.pid.lock().map_err(|_| "Workflow state unavailable.")?;
        *guard
    };

    let Some(pid) = pid else {
        return Ok(());
    };

    let output = Command::new("taskkill")
        .creation_flags(CREATE_NO_WINDOW)
        .args(["/PID", &pid.to_string(), "/T", "/F"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|error| error.to_string())?;

    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }

    let mut guard = state.pid.lock().map_err(|_| "Workflow state unavailable.")?;
    *guard = None;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(WorkflowState::default())
        .invoke_handler(tauri::generate_handler![
            get_snapshot,
            get_config,
            save_config,
            get_resume_inventory,
            import_resume,
            analyze_resume_profile,
            create_resume_profile,
            get_launch_context,
            get_workflow_status,
            start_workflow,
            stop_workflow
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
