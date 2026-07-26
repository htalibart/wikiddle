import process from "node:process";

const apiTarget = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default {
  server: {
    proxy: {
      "/api": apiTarget,
    },
  },
};
