export function moveImageToCover(items, index) {
  if (!Array.isArray(items) || index < 0 || index >= items.length) {
    return Array.isArray(items) ? [...items] : []
  }

  return [items[index], ...items.filter((_item, itemIndex) => itemIndex !== index)]
}

export function removeImageAt(items, index) {
  if (!Array.isArray(items)) return []
  return items.filter((_item, itemIndex) => itemIndex !== index)
}

export function getAdjacentImage(items, currentItem, direction) {
  if (!Array.isArray(items) || items.length === 0) return ""

  const currentIndex = Math.max(0, items.indexOf(currentItem))
  const offset = direction < 0 ? -1 : 1
  const nextIndex = (currentIndex + offset + items.length) % items.length
  return items[nextIndex]
}
