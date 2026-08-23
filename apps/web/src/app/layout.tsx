import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rio Preto em Dados",
  description:
    "Mobilidade urbana de São José do Rio Preto-SP com dados abertos e metodologia reproduzível.",
};

const NAV = [
  { href: "/", label: "Visão geral" },
  { href: "/ciclovias", label: "Ciclovias" },
  { href: "/quinze-minutos", label: "15 minutos" },
  { href: "/transporte", label: "Transporte" },
  { href: "/zoneamento", label: "Zoneamento" },
  { href: "/obras", label: "Obras" },
  { href: "/metodologia", label: "Metodologia" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen antialiased">
        <header className="border-b border-[var(--border)] bg-[var(--panel)]">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="font-semibold tracking-tight">
              Rio Preto em Dados
            </Link>
            <nav className="flex gap-1 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-1.5 text-[var(--muted)] transition-colors hover:bg-white/5 hover:text-[var(--text)]"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-[var(--muted)]">
          Fontes: Prefeitura de São José do Rio Preto (ArcGIS público), OpenStreetMap,
          IBGE Censo 2022. Metodologia aberta —{" "}
          <a
            className="underline hover:text-[var(--text)]"
            href="https://github.com/vncsleal/rio-preto-mobility"
          >
            repositório
          </a>
          .
        </footer>
      </body>
    </html>
  );
}
