import { useState } from "react";

interface Props {
  src: string | null | undefined;
  abbr: string | null | undefined;
  size?: "sm" | "md" | "lg";
}

/** Team logo over an initials badge. The badge shows until the image loads, and stays if it fails. */
export function Logo({ src, abbr, size = "md" }: Props) {
  const [status, setStatus] = useState<"loading" | "loaded" | "failed">(src ? "loading" : "failed");

  return (
    <span className={`logo ${size}`} aria-hidden="true">
      {status !== "loaded" && <span className="logo-fallback">{(abbr ?? "").slice(0, 4)}</span>}
      {src && status !== "failed" && (
        <img
          src={src}
          alt=""
          loading="lazy"
          onLoad={() => setStatus("loaded")}
          onError={() => setStatus("failed")}
        />
      )}
    </span>
  );
}
