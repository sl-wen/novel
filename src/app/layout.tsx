import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "小说下载器",
  description: "一个简单的小说下载工具",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
