import { TicketDashboard } from "@/components/ticket-dashboard";
import { loadInitialTickets } from "@/lib/backend";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const initialTickets = await loadInitialTickets();

  return <TicketDashboard initialTickets={initialTickets} />;
}
