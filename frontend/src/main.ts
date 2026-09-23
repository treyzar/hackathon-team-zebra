import "./assets/main.css";

import { createApp } from "vue";
import { createPinia } from "pinia";

import { setupApiInterceptors } from "@/api/interceptors";
import App from "./App.vue";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
setupApiInterceptors(pinia);
app.mount("#app");
