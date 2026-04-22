import React from "react";
import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import Bookmarklet from "@/components/Bookmarklet";
import Receipts from "@/components/Receipts";
import Playground from "@/components/Playground";
import PatternLibrary from "@/components/PatternLibrary";
import StatsPanel from "@/components/StatsPanel";
import Downloads from "@/components/Downloads";
import Feed from "@/components/Feed";
import Footer from "@/components/Footer";
import PrivacyBadge from "@/components/PrivacyBadge";
import PrivacyPage from "@/components/PrivacyPage";
import { Toaster } from "sonner";
import "@/App.css";

// Tiny path-based router. We don't need react-router for one static
// page — branch once at mount; the /privacy page is fully static.
const isPrivacyRoute =
  typeof window !== "undefined" && window.location.pathname === "/privacy";

function App() {
  return (
    <div className="App min-h-screen bg-[#0A0A0A] text-zinc-100 font-['IBM_Plex_Sans',sans-serif]">
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#121212",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#fafafa",
            fontFamily: "'JetBrains Mono', monospace",
            borderRadius: "2px",
          },
        }}
      />
      {isPrivacyRoute ? (
        <PrivacyPage />
      ) : (
        <>
          <Nav />
          <main>
            <Hero />
            <Bookmarklet />
            <Receipts />
            <Playground />
            <PatternLibrary />
            <StatsPanel />
            <Downloads />
            <Feed />
          </main>
          <Footer />
          <PrivacyBadge />
        </>
      )}
    </div>
  );
}

export default App;
