import type { Metadata } from "next";
import { Suspense } from "react";
import { PlainHeader } from "@/components/PlainHeader";
import { VerifyEmailView } from "./VerifyEmailView";

export const metadata: Metadata = { title: "Подтверждение почты" };

export default function VerifyEmailPage() {
  return (
    <>
      <PlainHeader href="/" label="В ленту" />
      <main id="main" style={{ maxWidth: 560, margin: "0 auto", padding: "56px 24px" }}>
        <Suspense>
          <VerifyEmailView />
        </Suspense>
      </main>
    </>
  );
}
