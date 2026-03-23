import api from './client'

export async function login(username, password) {
  const res = await api.post('/auth/login/', { username, password })
  return res.data
}

export async function getMe() {
  const res = await api.get('/auth/me/')
  return res.data
}
