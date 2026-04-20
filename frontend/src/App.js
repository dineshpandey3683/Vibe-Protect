import React from "react";
import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import Playground from "@/components/Playground";
import PatternLibrary from "@/components/PatternLibrary";
import StatsPanel from "@/components/StatsPanel";
import Downloads from "@/components/Downloads";
import Feed from "@/components/Feed";
import Footer from "@/components/Footer";
import { Toaster } from "sonner";
import "@/App.css";

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
      <Nav />
      <main>
        <Hero />
        <Playground />
        <PatternLibrary />
        <StatsPanel />
        <Downloads />
        <Feed />
      </main>
      <Footer />
    </div>
  );
}

export default App;
