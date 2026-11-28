// No ore under the sea floor: metals come from mob drops, ruin and city loot, and our own
// extraction from sea minerals. GregTech's veins may come back later in the vents or the Abyss.
GTCEuServerEvents.oreVeins(event => {
  event.removeAll()
})
