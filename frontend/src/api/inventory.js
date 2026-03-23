import api from './client'

export async function listIngredients(params = {}) {
  const res = await api.get('/ingredients/', { params })
  return res.data
}

export async function listStock(params = {}) {
  const res = await api.get('/stock/', { params })
  return res.data
}

export async function listMovements(params = {}) {
  const res = await api.get('/movements/', { params })
  return res.data
}
