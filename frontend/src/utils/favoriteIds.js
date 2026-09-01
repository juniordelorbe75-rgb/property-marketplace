export function updateFavoriteIds(currentIds, propertyId, shouldAdd) {
  const next = new Set(currentIds)
  if (shouldAdd) next.add(Number(propertyId))
  else next.delete(Number(propertyId))
  return next
}
