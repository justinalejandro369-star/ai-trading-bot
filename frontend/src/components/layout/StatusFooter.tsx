import { useEffect, useState } from "react";

export default function StatusFooter() {
  const [utcTime, setUtcTime] = useState(() => formatUTC());

  useEffect(() => {
    const id = setInterval(() => setUtcTime(formatUTC()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <footer className="shrink-0 w-full flex items-center justify-between px-4 bg-[#0B0E11] border-t border-[#424654]/15 h-8 font-['Inter'] text-[10px] font-mono">
      {/* Left: system health + exchange statuses */}
      <div className="flex items-center gap-2">
        {/* Green dot + System Health */}
        <span className="flex items-center gap-1.5 text-[#44E092]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#44E092]" />
          System Health: Optimal
        </span>

        <span className="text-[#424654]">|</span>

        {/* Exchange statuses */}
        <div className="hidden md:flex items-center gap-2 text-[#C3C6D7]">
          <span>Finnhub: Connected</span>
          <span>CoinGecko: Connected</span>
          <span>CCXT: Connected</span>
        </div>
      </div>

      {/* Right: Daily P&L, latency, UTC clock */}
      <div className="flex items-center gap-3 text-[#C3C6D7]">
        <span className="font-bold">Daily P&amp;L: --</span>
        <span>LATENCY: 14MS</span>
        <span>{utcTime}</span>
      </div>
    </footer>
  );
}

/** Format current time as HH:MM:SS UTC */
function formatUTC(): string {
  const now = new Date();
  return now.toISOString().slice(11, 19) + " UTC";
}
