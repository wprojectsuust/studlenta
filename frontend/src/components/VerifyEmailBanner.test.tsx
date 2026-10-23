import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";
import { VerifyEmailBanner } from "./VerifyEmailBanner";

describe("VerifyEmailBanner", () => {
  it("explains where the letter went and resends it", async () => {
    const resend = vi.fn().mockResolvedValue({ sent: true });
    render(<VerifyEmailBanner email="anna@uust.ru" onResend={resend} />);
    const banner = screen.getByRole("region", { name: "Подтвердите почту" });
    expect(banner).toHaveTextContent("anna@uust.ru");
    expect(banner).toHaveTextContent("Спам");
    await userEvent.click(screen.getByRole("button", { name: "Отправить ещё раз" }));
    expect(resend).toHaveBeenCalledOnce();
    expect(screen.getByRole("status")).toHaveTextContent("Письмо отправлено");
  });

  it("shows the cooldown message from the server", async () => {
    const resend = vi.fn().mockRejectedValue(new ApiError(409, "conflict", "Письмо уже отправлено — повторить можно через минуту"));
    render(<VerifyEmailBanner email="anna@uust.ru" onResend={resend} />);
    await userEvent.click(screen.getByRole("button", { name: "Отправить ещё раз" }));
    expect(screen.getByRole("status")).toHaveTextContent("через минуту");
  });
});
