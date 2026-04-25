import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import History from "./pages/History";
import Sensitivity from "./pages/Sensitivity";
import Methodology from "./pages/Methodology";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60_000, refetchOnWindowFocus: false } },
});

function Shell() {
  return (
    <div className="app">
      <header>
        <h1>Housing Fair Value</h1>
        <nav>
          <NavLink to="/">History</NavLink>
          <NavLink to="/sensitivity">Sensitivity</NavLink>
          <NavLink to="/methodology">Methodology</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<History />} />
          <Route path="/sensitivity" element={<Sensitivity />} />
          <Route path="/methodology" element={<Methodology />} />
        </Routes>
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
