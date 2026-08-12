import AppShell from '@/components/AppShell';

export default function OwnerLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}