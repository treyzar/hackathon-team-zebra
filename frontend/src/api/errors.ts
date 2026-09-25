import axios from "axios";

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof Error && !axios.isAxiosError(error)) return error.message;
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first.msg === "string") return first.msg;
    }
  }

  return "Не удалось выполнить запрос. Проверьте подключение и попробуйте ещё раз.";
}
