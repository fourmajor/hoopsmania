import './globals.css';

export const metadata = {
  title: 'Hoops Mania',
  description: 'AI-driven global basketball simulation game'
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
