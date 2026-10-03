import type { ReactNode } from "react";

interface Props {
  title: string;
  count?: number;
  sub?: string;
  className?: string;
  children: ReactNode;
}

export function Section({ title, count, sub, className = "", children }: Props) {
  return (
    <section className={`block ${className}`.trim()}>
      <div className="sec-head">
        <h2>{title}</h2>
        {count !== undefined && <span className="count">{count === 1 ? "1 game" : `${count} games`}</span>}
        {sub && <span className="count">{sub}</span>}
      </div>
      <div className="rows">{children}</div>
    </section>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}
