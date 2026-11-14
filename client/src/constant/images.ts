/**
 * Stock photos (Unsplash) for the public pages. They illustrate the kind of
 * food people can order; they are not any particular restaurant's dishes.
 * Swap them for photos of your own restaurants when you have them.
 */
const unsplash = (id: string, width = 1200) =>
    `https://images.unsplash.com/${id}?q=75&w=${width}&auto=format&fit=crop`;

const images = {
    heroGrill: unsplash('photo-1599487488170-d11ec9c172f0', 1800),      // skewers on the grill
    shisanyama: unsplash('photo-1555939594-58d7cb561ad1'),               // grilled meat spread
    chicken: unsplash('photo-1712579733874-c3a79f0f9d12'),               // grilled chicken
    ribsAndChips: unsplash('photo-1544025162-d76694265947'),             // ribs, chips and salad
    burgers: unsplash('photo-1550547660-d9450f859349'),                  // burgers
    pizza: unsplash('photo-1585238342024-78d387f4a707'),                 // pizza
    plates: unsplash('photo-1504674900247-0877df9cc836'),                // table of dishes
};

export default images;
