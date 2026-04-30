import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000
})

export const configApi = {
  getWeights: () => api.get('/api/config/weights'),
  updateWeights: (weights) => api.put('/api/config/weights', weights),
  getThreshold: () => api.get('/api/config/threshold'),
  updateThreshold: (threshold) => api.put('/api/config/threshold', { threshold })
}

export const patientsApi = {
  list: (page, pageSize) => api.get('/api/patients', { params: { page, page_size: pageSize } }),
  get: (patientId) => api.get(`/api/patients/${patientId}`),
  getSimilar: (patientId) => api.get(`/api/patients/${patientId}/similar`),
  getMaster: (patientId) => api.get(`/api/patients/${patientId}/master`)
}

export const mergeApi = {
  listCandidates: (page, pageSize) => api.get('/api/merge/candidates', { params: { page, page_size: pageSize } }),
  merge: (personIdA, personIdB) => api.post('/api/merge', { person_id_a: personIdA, person_id_b: personIdB }),
  ignore: (id) => api.post(`/api/merge/${id}/ignore`),
  history: (page, pageSize) => api.get('/api/merge/history', { params: { page, page_size: pageSize } })
}

export const statsApi = {
  get: () => api.get('/api/stats'),
  getTrend: (days) => api.get('/api/stats/trend', { params: { days } })
}

export default api