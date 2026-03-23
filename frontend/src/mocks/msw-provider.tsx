"use client";

import { useState, useEffect } from "react";

export function MswProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(
    process.env.NEXT_PUBLIC_ENABLE_MSW !== "true"
  );

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_ENABLE_MSW !== "true") return;

    import("./init").then(({ initMsw }) =>
      initMsw().then(() => setReady(true))
    );
  }, []);

  if (!ready) return null;

  return <>{children}</>;
}
