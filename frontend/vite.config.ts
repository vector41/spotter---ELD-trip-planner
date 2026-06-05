import path from "path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function stripTrailingSlash(url: string) {
  return url.replace(/\/$/, "");
}

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(__dirname, "..");
  const env = loadEnv(mode, rootDir, "");
  const isVercel = Boolean(env.VERCEL);
  const backendUrl = isVercel
    ? ""
    : stripTrailingSlash(env.BACKEND_URL || "http://127.0.0.1:8000");
  const useProxy =
    mode === "development" && !env.FORCE_DIRECT_API && !isVercel;

  return {
    plugins: [react()],
    envDir: rootDir,
    define: {
      "import.meta.env.VITE_BACKEND_URL": JSON.stringify(backendUrl),
      "import.meta.env.VITE_USE_API_PROXY": JSON.stringify(useProxy),
    },
    server: {
      host: true,
      port: Number(env.VITE_DEV_PORT) || 5173,
      strictPort: true,
      proxy: useProxy
        ? {
            "/api": {
              target: backendUrl,
              changeOrigin: true,
            },
          }
        : undefined,
    },
  };
});
