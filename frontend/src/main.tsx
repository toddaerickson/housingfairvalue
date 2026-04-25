import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ErrorBoundary from "./components/ErrorBoundary";
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
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            History
          </NavLink>
          <NavLink to="/sensitivity" className={({ isActive }) => (isActive ? "active" : "")}>
            Sensitivity
          </NavLink>
          <NavLink to="/methodology" className={({ isActive }) => (isActive ? "active" : "")}>
            Methodology
          </NavLink>
        </nav>
      </header>
      <main>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<History />} />
            <Route path="/sensitivity" element={<Sensitivity />} />
            <Route path="/methodology" element={<Methodology />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error('#root element missing in index.html');
ReactDOM.createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
