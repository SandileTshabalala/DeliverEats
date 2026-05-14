export const Roles = {
  SUPER_ADMIN: "super_admin",
  ADMIN: "admin",
  RESTAURANT_ADMIN: "restaurant_admin",
  CUSTOMER: "customer",
  DRIVER: "driver",
} as const;

export type Role = typeof Roles[keyof typeof Roles];
