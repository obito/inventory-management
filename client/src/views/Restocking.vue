<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
        </div>
        <div class="budget-slider-row">
          <input
            type="range"
            class="budget-slider"
            min="0"
            max="100000"
            step="500"
            v-model.number="budget"
          />
          <span class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }}</h3>
        </div>
        <p class="fit-summary">
          {{ t('restocking.itemsFitBudget', { picked: recommendedItems.length, eligible: eligibleItems.length }) }}
        </p>

        <div v-if="eligibleItems.length === 0" class="no-items">
          {{ t('restocking.noItemsAffordable') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in rankedItems"
                :key="item.item_sku"
                :class="{ 'row-included': isRecommended(item.item_sku), 'row-excluded': !isRecommended(item.item_sku) }"
              >
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toFixed(2) }}</td>
                <td>{{ currencySymbol }}{{ (item.forecasted_demand * item.unit_cost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td>
                  <span :class="['badge', item.trend]">
                    {{ t(`trends.${item.trend}`) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="order-summary">
          <div class="summary-row">
            <span class="summary-label">{{ t('restocking.totalCost') }}</span>
            <span class="summary-value">{{ currencySymbol }}{{ totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
          </div>
          <div class="summary-row">
            <span class="summary-label">{{ t('restocking.remainingBudget') }}</span>
            <span class="summary-value">{{ currencySymbol }}{{ remainingBudget.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
          </div>

          <button
            class="place-order-btn"
            :disabled="recommendedItems.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>

          <div v-if="confirmation" class="confirmation">{{ confirmation }}</div>
          <div v-if="submitError" class="error">{{ submitError }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitError = ref(null)
    const confirmation = ref(null)

    const forecasts = ref([])
    const budget = ref(0)

    const loadForecasts = async () => {
      try {
        loading.value = true
        forecasts.value = await api.getDemandForecasts()
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Items with decreasing demand are excluded from restocking recommendations entirely
    const eligibleItems = computed(() => {
      return forecasts.value.filter(f => f.trend !== 'decreasing')
    })

    // Rank by the size of the demand gap (biggest gap first) so the budget goes to the
    // items with the most urgent growing need
    const rankedItems = computed(() => {
      return [...eligibleItems.value].sort((a, b) => {
        return (b.forecasted_demand - b.current_demand) - (a.forecasted_demand - a.current_demand)
      })
    })

    // Greedily walk the ranked list, taking every item that still fits the remaining
    // budget and skipping (not stopping on) ones that don't, so cheaper items further
    // down the ranking still get a chance
    const recommendedItems = computed(() => {
      const picked = []
      let remaining = budget.value

      for (const item of rankedItems.value) {
        const cost = item.forecasted_demand * item.unit_cost
        if (cost <= remaining) {
          picked.push({
            item_sku: item.item_sku,
            item_name: item.item_name,
            quantity: item.forecasted_demand,
            unit_cost: item.unit_cost,
            line_total: cost
          })
          remaining -= cost
        }
      }

      return picked
    })

    const recommendedSkus = computed(() => new Set(recommendedItems.value.map(item => item.item_sku)))
    const isRecommended = (sku) => recommendedSkus.value.has(sku)

    const totalCost = computed(() => {
      return recommendedItems.value.reduce((sum, item) => sum + item.line_total, 0)
    })

    const remainingBudget = computed(() => budget.value - totalCost.value)

    const placeOrder = async () => {
      if (recommendedItems.value.length === 0 || submitting.value) return

      submitting.value = true
      submitError.value = null
      confirmation.value = null

      try {
        const order = await api.createRestockingOrder({
          budget: budget.value,
          items: recommendedItems.value.map(item => ({
            item_sku: item.item_sku,
            item_name: item.item_name,
            quantity: item.quantity,
            unit_cost: item.unit_cost,
            line_total: item.line_total
          }))
        })
        confirmation.value = t('restocking.orderPlaced', { orderNumber: order.order_number })
        budget.value = 0
      } catch (err) {
        submitError.value = 'Failed to submit restocking order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      loading,
      error,
      submitting,
      submitError,
      confirmation,
      currencySymbol,
      budget,
      eligibleItems,
      rankedItems,
      recommendedItems,
      isRecommended,
      totalCost,
      remainingBudget,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-slider-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.budget-slider {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  accent-color: #3b82f6;
  cursor: pointer;
}

.budget-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 120px;
  text-align: right;
}

.fit-summary {
  color: #64748b;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.no-items {
  color: #64748b;
  font-size: 0.938rem;
  padding: 1.5rem 0;
  text-align: center;
}

.row-included {
  background: #f0fdf4;
}

.row-excluded {
  color: #94a3b8;
  opacity: 0.6;
}

.order-summary {
  margin-top: 1.25rem;
  padding-top: 1.25rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.938rem;
}

.summary-label {
  color: #64748b;
  font-weight: 600;
}

.summary-value {
  color: #0f172a;
  font-weight: 700;
}

.place-order-btn {
  margin-top: 0.75rem;
  align-self: flex-start;
  padding: 0.625rem 1.5rem;
  border: none;
  border-radius: 6px;
  background: #3b82f6;
  color: white;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.confirmation {
  color: #065f46;
  background: #d1fae5;
  border: 1px solid #a7f3d0;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}
</style>
