import axios from "axios";

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }
  }

  return "Не удалось выполнить запрос. Проверьте подключение и попробуйте ещё раз.";
}
