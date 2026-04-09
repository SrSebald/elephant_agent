import { TicketDashboard } from "@/components/ticket-dashboard";
import { loadInitialContext, loadInitialSummary, loadInitialTickets } from "@/lib/backend";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [initialTickets, initialSummary, initialContext] = await Promise.all([
    loadInitialTickets(),
    loadInitialSummary(),
    loadInitialContext(),
  ]);

  return (
    <TicketDashboard
      initialTickets={initialTickets}
      initialSummary={initialSummary}
      initialContext={initialContext}
    />
  );
}
