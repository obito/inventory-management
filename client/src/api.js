import axios from 'axios'

// Overridable so the app can run against a backend on a non-default port
// (e.g. several git worktrees served side by side). Defaults to the standard port.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api'

// Serializes the global filters, dropping any set to 'all'. `fields` limits which
// filters an endpoint accepts - inventory has no time or status dimension.
function buildFilterParams(filters = {}, fields = ['warehouse', 'category', 'status', 'month']) {
  const params = new URLSearchParams()
  for (const field of fields) {
    if (filters[field] && filters[field] !== 'all') params.append(field, filters[field])
  }
  return params.toString()
}

export const api = {
  async getInventory(filters = {}) {
    const response = await axios.get(`${API_BASE_URL}/inventory?${buildFilterParams(filters, ['warehouse', 'category'])}`)
    return response.data
  },

  async getInventoryItem(id) {
    const response = await axios.get(`${API_BASE_URL}/inventory/${id}`)
    return response.data
  },

  async getOrders(filters = {}) {
    const response = await axios.get(`${API_BASE_URL}/orders?${buildFilterParams(filters)}`)
    return response.data
  },

  async getOrder(id) {
    const response = await axios.get(`${API_BASE_URL}/orders/${id}`)
    return response.data
  },

  async getDemandForecasts() {
    const response = await axios.get(`${API_BASE_URL}/demand`)
    return response.data
  },

  async getBacklog() {
    const response = await axios.get(`${API_BASE_URL}/backlog`)
    return response.data
  },

  async getDashboardSummary(filters = {}) {
    const response = await axios.get(`${API_BASE_URL}/dashboard/summary?${buildFilterParams(filters)}`)
    return response.data
  },

  async getSpendingSummary() {
    const response = await axios.get(`${API_BASE_URL}/spending/summary`)
    return response.data
  },

  async getMonthlySpending() {
    const response = await axios.get(`${API_BASE_URL}/spending/monthly`)
    return response.data
  },

  async getCategorySpending() {
    const response = await axios.get(`${API_BASE_URL}/spending/categories`)
    return response.data
  },

  async getTransactions() {
    const response = await axios.get(`${API_BASE_URL}/spending/transactions`)
    return response.data
  },

  async getQuarterlyReports(filters = {}) {
    const response = await axios.get(`${API_BASE_URL}/reports/quarterly?${buildFilterParams(filters)}`)
    return response.data
  },

  async getMonthlyTrends(filters = {}) {
    const response = await axios.get(`${API_BASE_URL}/reports/monthly-trends?${buildFilterParams(filters)}`)
    return response.data
  },

  async getTasks() {
    const response = await axios.get(`${API_BASE_URL}/tasks`)
    return response.data
  },

  async createTask(taskData) {
    const response = await axios.post(`${API_BASE_URL}/tasks`, taskData)
    return response.data
  },

  async deleteTask(taskId) {
    const response = await axios.delete(`${API_BASE_URL}/tasks/${taskId}`)
    return response.data
  },

  async toggleTask(taskId) {
    const response = await axios.patch(`${API_BASE_URL}/tasks/${taskId}`)
    return response.data
  },

  async createPurchaseOrder(purchaseOrderData) {
    const response = await axios.post(`${API_BASE_URL}/purchase-orders`, purchaseOrderData)
    return response.data
  },

  async getPurchaseOrderByBacklogItem(backlogItemId) {
    const response = await axios.get(`${API_BASE_URL}/purchase-orders/${backlogItemId}`)
    return response.data
  },

  async createRestockingOrder(payload) {
    const response = await axios.post(`${API_BASE_URL}/restocking-orders`, payload)
    return response.data
  },

  async getRestockingOrders() {
    const response = await axios.get(`${API_BASE_URL}/restocking-orders`)
    return response.data
  }
}
