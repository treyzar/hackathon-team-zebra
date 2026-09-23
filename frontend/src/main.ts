import "./assets/main.css";

import { createApp } from "vue";
import { createPinia } from "pinia";

import { setupApiInterceptors } from "@/api/interceptors";
import { createAppRouter } from "@/router";
import App from "./App.vue";

const app = createApp(App);
const pinia = createPinia();
const router = createAppRouter(pinia);

app.use(pinia);
setupApiInterceptors(pinia);
app.use(router);
app.mount("#app");
