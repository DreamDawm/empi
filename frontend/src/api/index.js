import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8808',
  timeout: 30000
})

export const configApi = {
  getWeights: () => api.get('/api/config/weights'),
  updateWeights: (weights) => api.put('/api/config/weights', weights),
  getThreshold: () => api.get('/api/config/threshold'),
  updateThreshold: (threshold) => api.put('/api/config/threshold', { threshold }),
  getPendingThreshold: () => api.get('/api/config/pending-threshold'),
  updatePendingThreshold: (threshold) => api.put('/api/config/pending-threshold', { threshold }),
  getPatientFields: () => api.get('/api/config/patient-fields'),
  getPollInterval: () => api.get('/api/config/poll-interval'),
  updatePollInterval: (hours) => api.put('/api/config/poll-interval', { hours })
}

export const patientsApi = {
  list: (page, pageSize) => api.get('/api/patients', { params: { page, page_size: pageSize } }),
  get: (patientId) => api.get(`/api/patients/${patientId}`),
  getSimilar: (patientId) => api.get(`/api/patients/${patientId}/similar`),
  getMaster: (patientId) => api.get(`/api/patients/${patientId}/master`)
}

export const mergeApi = {
  listCandidates: (page, pageSize, minScore = 0) => api.get('/api/merge/candidates', { params: { page, page_size: pageSize, min_score: minScore } }),
  merge: (personIdA, personIdB) => api.post('/api/merge', { person_id_a: personIdA, person_id_b: personIdB }),
  ignore: (id) => api.post(`/api/merge/${id}/ignore`),
  history: (page, pageSize) => api.get('/api/merge/history', { params: { page, page_size: pageSize } })
}

export const statsApi = {
  get: () => api.get('/api/stats'),
  getTrend: (days) => api.get('/api/stats/trend', { params: { days } }),
  // Use async endpoints to avoid timeout - returns immediately while clean runs in background
  triggerClean: () => api.post('/api/stats/trigger-clean-async'),
  triggerFullClean: () => api.post('/api/stats/trigger-full-clean-async')
}

export default api