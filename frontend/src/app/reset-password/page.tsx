import type { Metadata } from "next";
import { Suspense } from "react";
import { PlainHeader } from "@/components/PlainHeader";
import { ResetPasswordForm } from "./ResetPasswordForm";

export const metadata: Metadata = { title: "Новый пароль" };

export default function ResetPasswordPage() {
  return (
    <>
      <PlainHeader href="/login" label="Ко входу" />
      <main id="main" style={{ maxWidth: 480, margin: "0 auto", padding: "56px 24px" }}>
        <Suspense>
          <ResetPasswordForm />
        </Suspense>
      </main>
    </>
  );
}
