import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextVitals,
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  {
    rules: {
      // Sessions live in localStorage and the URL, which only exist in the
      // browser, so pages have to read them in an effect after hydration.
      "react-hooks/set-state-in-effect": "off",
      // Navigation after login, logout and Stripe redirects is deliberately a
      // full page load, which resets all client state.
      "react-hooks/immutability": "off",
      "@next/next/no-location-assign-relative-destination": "off",
      "@next/next/no-html-link-for-pages": "off",
    },
  },
];

export default config;
