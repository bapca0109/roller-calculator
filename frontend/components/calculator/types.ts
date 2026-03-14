// Calculator types and constants

export interface Attachment {
  uri: string;
  name: string;
  type: string;
  base64?: string;
}

export interface RollerStandards {
  pipe_diameters: number[];
  shaft_diameters: number[];
  bearing_options: { [key: string]: string[] };
  roller_lengths_by_belt_width: { [key: string]: number[] };
  pipe_shaft_compatibility?: { [key: string]: number[] };
}

export interface CostResult {
  configuration: {
    product_code: string;
    roller_type: string;
    pipe_diameter_mm: number;
    pipe_length_mm: number;
    pipe_type: string;
    shaft_diameter_mm: number;
    shaft_length_mm: number;
    bearing: string;
    bearing_make: string;
    housing: string;
    rubber_diameter_mm?: number;
    quantity: number;
  };
  cost_breakdown: {
    pipe_cost: number;
    shaft_cost: number;
    bearing_cost: number;
    housing_cost: number;
    seal_cost: number;
    circlip_cost: number;
    rubber_cost?: number;
    locking_ring_cost?: number;
    total_raw_material: number;
    single_roller_weight_kg?: number;
    total_weight_kg?: number;
  };
  pricing: {
    raw_material_cost: number;
    layout_cost: number;
    profit: number;
    unit_price: number;
    quantity: number;
    order_value: number;
    discount_percent: number;
    discount_amount: number;
    price_after_discount: number;
    packing_type: string;
    packing_percent: number;
    packing_charges: number;
    final_price: number;
  };
  freight?: {
    destination_pincode: string;
    dispatch_pincode: string;
    distance_km: number;
    single_roller_weight_kg: number;
    total_weight_kg: number;
    freight_rate_per_kg: number;
    freight_charges: number;
  };
  gst?: {
    taxable_amount: number;
    gst_type: string;
    cgst_rate: number;
    cgst_amount: number;
    sgst_rate: number;
    sgst_amount: number;
    igst_rate: number;
    igst_amount: number;
    total_gst: number;
    destination_state: string;
    is_same_state: boolean;
  };
  grand_total: number;
  // Optional fields added when item is added to cart
  attachments?: Attachment[];
  remark?: string | null;
}

export interface CalculatorErrors {
  pipeLength?: string;
  quantity?: string;
  freightPincode?: string;
}

// Dropdown options
export const PIPE_TYPES = [
  { label: 'Type A (Light)', value: 'A' },
  { label: 'Type B (Medium)', value: 'B' },
  { label: 'Type C (Heavy)', value: 'C' },
];

export const BEARING_MAKES = [
  { label: 'China', value: 'china' },
  { label: 'SKF', value: 'skf' },
  { label: 'FAG', value: 'fag' },
  { label: 'Timken', value: 'timken' },
];

export const PACKING_TYPES = [
  { label: 'Standard (1%)', value: 'standard' },
  { label: 'Pallet (4%)', value: 'pallet' },
  { label: 'Wooden Box (8%)', value: 'wooden_box' },
];

// Rubber diameter options per pipe diameter (for impact rollers)
export const RUBBER_DIAMETERS: { [key: number]: number[] } = {
  60.8: [90, 114],
  76.1: [114, 127, 140],
  88.9: [127, 140, 152],
  114.3: [139, 152, 165, 190],
  127.0: [165, 190],
  139.7: [165, 190],
  152.4: [190],
};

// Roller type labels
export const ROLLER_TYPES = {
  carrying: 'Carrying',
  impact: 'Impact',
  return: 'Return',
} as const;

export type RollerType = keyof typeof ROLLER_TYPES;
