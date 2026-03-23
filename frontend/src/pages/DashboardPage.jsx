import { useQuery } from '@tanstack/react-query'
import { listIngredients, listStock } from '../api/inventory'

function Card({ title, value, subtitle }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600">{title}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
      {subtitle ? <div className="mt-1 text-xs text-slate-500">{subtitle}</div> : null}
    </div>
  )
}

export default function DashboardPage() {
  const lowStock = useQuery({
    queryKey: ['ingredients', { low_stock: true }],
    queryFn: () => listIngredients({ low_stock: true, page_size: 1 }),
  })

  const expiringSoon = useQuery({
    queryKey: ['stock', { expiring_soon: true }],
    queryFn: () => listStock({ expiring_soon: true, page_size: 1 }),
  })

  const expired = useQuery({
    queryKey: ['stock', { expired: true }],
    queryFn: () => listStock({ expired: true, page_size: 1 }),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card
          title="Low stock ingredients"
          value={lowStock.isLoading ? '…' : lowStock.data?.count ?? 0}
          subtitle="Across all locations"
        />
        <Card
          title="Expiring soon"
          value={expiringSoon.isLoading ? '…' : expiringSoon.data?.count ?? 0}
          subtitle="Next 7 days"
        />
        <Card
          title="Expired"
          value={expired.isLoading ? '…' : expired.data?.count ?? 0}
          subtitle="Needs waste reporting"
        />
      </div>

      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-900">Next steps</div>
        <div className="mt-2 text-sm text-slate-600">
          Use the Inventory page to review ingredients and stock, and the Admin panel for full CRUD while the
          frontend is being built out.
        </div>
      </div>
    </div>
  )
}
