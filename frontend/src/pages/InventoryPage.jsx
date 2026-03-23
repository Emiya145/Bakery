import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listIngredients } from '../api/inventory'

export default function InventoryPage() {
  const [search, setSearch] = useState('')

  const queryParams = useMemo(() => {
    const params = {}
    if (search.trim()) params.search = search.trim()
    params.ordering = 'name'
    return params
  }, [search])

  const ingredients = useQuery({
    queryKey: ['ingredients', queryParams],
    queryFn: () => listIngredients(queryParams),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Inventory</h1>
          <div className="mt-1 text-sm text-slate-600">Ingredients overview.</div>
        </div>
        <div className="w-64">
          <label className="block text-xs font-medium text-slate-600">Search</label>
          <input
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="e.g. flour"
          />
        </div>
      </div>

      <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b">
          <div className="text-sm font-semibold text-slate-900">Ingredients</div>
        </div>

        {ingredients.isLoading ? (
          <div className="p-4 text-sm text-slate-600">Loading…</div>
        ) : ingredients.isError ? (
          <div className="p-4 text-sm text-red-700">Failed to load ingredients.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Unit</th>
                  <th className="px-4 py-3">Total stock</th>
                  <th className="px-4 py-3">Reorder level</th>
                  <th className="px-4 py-3">Low?</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(ingredients.data?.results || []).map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{row.name}</td>
                    <td className="px-4 py-3 text-slate-700">{row.unit}</td>
                    <td className="px-4 py-3 text-slate-700">{row.total_stock}</td>
                    <td className="px-4 py-3 text-slate-700">{row.reorder_level}</td>
                    <td className="px-4 py-3">
                      {row.is_low_stock ? (
                        <span className="inline-flex rounded-full bg-red-100 px-2 py-1 text-xs font-semibold text-red-800">
                          Low
                        </span>
                      ) : (
                        <span className="inline-flex rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800">
                          OK
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="text-xs text-slate-500">
        Tip: For now, create/update ingredients via Django Admin. This table reflects the API.
      </div>
    </div>
  )
}
