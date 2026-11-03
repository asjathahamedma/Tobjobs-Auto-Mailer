import { Suspense } from "react";
import { AuthForm } from "@/components/AuthForm";

export default function LoginPage() {
  return <Suspense fallback={<main className="auth-page"><p>Loading sign-in…</p></main>}><AuthForm /></Suspense>;
}
