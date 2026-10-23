import type { Metadata } from "next";
import { PlainHeader } from "@/components/PlainHeader";
import { ForgotPasswordForm } from "./ForgotPasswordForm";

export const metadata: Metadata = { title: "Восстановление пароля" };

export default function ForgotPasswordPage() {
  return (
    <>
      <PlainHeader href="/login" label="Ко входу" />
      <main id="main" style={{ maxWidth: 480, margin: "0 auto", padding: "56px 24px" }}>
        <ForgotPasswordForm />
      </main>
    </>
  );
}
