import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // CYTE Risk Suite palette (Large Corporate Handbook)
        cyte: {
          navy: "#001080",
          navyHover: "#102090",
          navyDark: "#000860",
          panel: "#DBE3F1",
          lavender: "#C7CAE5",
          ragGreen: "#30A020",
          ragGreenBg: "#E6F4E2",
          ragAmber: "#B57E00",
          ragAmberBg: "#FFF3D6",
          ragRed: "#D04040",
          ragRedBg: "#FFD7D7",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
