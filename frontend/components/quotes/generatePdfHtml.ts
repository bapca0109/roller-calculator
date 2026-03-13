// PDF HTML generation for quotes - SYNCED WITH BACKEND FORMAT
import { Quote } from './types';
import { formatDate } from './utils';

interface GeneratePdfOptions {
  isCustomer: boolean;
}

// Helper to format numbers with commas (matching backend)
const formatNumber = (num: number): string => {
  return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// Get current timestamp in IST format
const getReportTimestamp = (): string => {
  const now = new Date();
  const options: Intl.DateTimeFormatOptions = {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata'
  };
  return now.toLocaleString('en-IN', options) + ' IST';
};

export const generatePdfHtml = (quote: Quote, options: GeneratePdfOptions): string => {
  const { isCustomer } = options;
  
  // Determine document label based on quote number prefix
  const isRfq = quote.quote_number?.startsWith('RFQ');
  const pdfDocLabelFull = isRfq ? 'REQUEST FOR QUOTATION' : 'QUOTATION';
  
  // Use approval date for approved quotes, otherwise use created date
  const isApproved = quote.status?.toLowerCase() === 'approved';
  const displayDate = isApproved && (quote.approved_at_ist || quote.approved_at)
    ? (quote.approved_at_ist || formatDate(quote.approved_at || ''))
    : (quote.created_at_ist || formatDate(quote.created_at));
  
  // Check if prices should be hidden (for customers viewing unapproved quotes)
  const shouldHidePrices = isCustomer && !isApproved;
  
  // Report generated timestamp
  const reportGenerated = getReportTimestamp();
  
  // ALWAYS use item-level discount format for PDF display
  const useItemDiscounts = true;
  
  // Calculate overall discount percentage for items without individual discounts
  const overallDiscountPercent = quote.subtotal > 0 ? (quote.total_discount / quote.subtotal) * 100 : 0;
  const hasPerItemDiscounts = quote.use_item_discounts;
  
  // Calculate totals with item discounts
  let calculatedSubtotal = 0;
  let totalItemDiscount = 0;
  let grandTotalWeight = 0;
  
  const productsHtml = quote.products.map((product, index) => {
    // Use individual item discount if available, otherwise use overall discount percentage
    let itemDiscountPercent = 0;
    if (hasPerItemDiscounts && product.item_discount_percent !== undefined) {
      itemDiscountPercent = product.item_discount_percent;
    } else if (quote.total_discount > 0 && quote.subtotal > 0) {
      itemDiscountPercent = overallDiscountPercent;
    }
    
    const valueAfterDiscount = product.unit_price * (1 - itemDiscountPercent / 100);
    const lineTotal = product.quantity * valueAfterDiscount;
    const originalAmount = product.quantity * product.unit_price;
    const itemDiscountAmount = originalAmount - lineTotal;
    
    calculatedSubtotal += lineTotal;
    totalItemDiscount += itemDiscountAmount;
    
    // Get weight info from specifications OR from product directly
    const unitWeight = product.weight_kg || product.specifications?.weight_kg || product.specifications?.single_roller_weight_kg || 0;
    const totalWeight = unitWeight * product.quantity;
    grandTotalWeight += totalWeight;
    
    // Format weight display
    const unitWeightStr = unitWeight > 0 ? unitWeight.toFixed(2) : '-';
    const totalWeightStr = totalWeight > 0 ? totalWeight.toFixed(2) : '-';
    
    // Build specs HTML
    let specsHtml = '';
    if (product.specifications) {
      const specParts = [];
      if (product.specifications.roller_type) specParts.push(`Type: ${product.specifications.roller_type}`);
      if (product.specifications.pipe_diameter) specParts.push(`Pipe: ${product.specifications.pipe_diameter}mm`);
      if (product.specifications.shaft_diameter) specParts.push(`Shaft: ${product.specifications.shaft_diameter}mm`);
      if (product.specifications.bearing) specParts.push(`Bearing: ${product.specifications.bearing}`);
      if (specParts.length > 0) {
        specsHtml = `<div class="product-specs">${specParts.join(' | ')}</div>`;
      }
    }
    
    const remarkHtml = product.remark ? `<div class="product-remark">Note: ${product.remark}</div>` : '';
    
    // For RFQ (prices hidden) - show weight columns but no price columns
    if (shouldHidePrices) {
      return `
        <tr>
          <td class="cell-center">${index + 1}</td>
          <td class="cell-left">
            <div class="product-name">${product.product_id}</div>
            ${specsHtml}
            ${remarkHtml}
          </td>
          <td class="cell-center">${product.quantity}</td>
          <td class="cell-right">${unitWeightStr}</td>
          <td class="cell-right">${totalWeightStr}</td>
        </tr>
      `;
    }
    
    // Full row with weight columns (matching backend format)
    return `
      <tr>
        <td class="cell-center">${index + 1}</td>
        <td class="cell-left">
          <div class="product-name">${product.product_id}</div>
          ${specsHtml}
          ${remarkHtml}
        </td>
        <td class="cell-center">${product.quantity}</td>
        <td class="cell-right">${unitWeightStr}</td>
        <td class="cell-right">${totalWeightStr}</td>
        <td class="cell-right">Rs. ${formatNumber(valueAfterDiscount)}</td>
        <td class="cell-right"><strong>Rs. ${formatNumber(lineTotal)}</strong></td>
      </tr>
    `;
  }).join('');

  // Calculate totals
  const subtotalAfterDiscount = calculatedSubtotal;
  const packing = quote.packing_charges || 0;
  const shipping = quote.shipping_cost || 0;
  const taxableAmount = subtotalAfterDiscount + packing + shipping;
  const cgst = taxableAmount * 0.09;
  const sgst = taxableAmount * 0.09;
  const grandTotal = taxableAmount * 1.18;
  
  // Dynamic table header (matching backend format with weight columns)
  const tableHeader = shouldHidePrices ? `
    <tr>
      <th style="width: 6%;">#</th>
      <th style="width: 50%; text-align: left;">Description</th>
      <th style="width: 10%;">Qty</th>
      <th style="width: 14%; text-align: right;">Wt/Pc (kg)</th>
      <th style="width: 14%; text-align: right;">Total Wt</th>
    </tr>
  ` : `
    <tr>
      <th style="width: 4%;">SR.</th>
      <th style="width: 24%; text-align: left;">ITEM CODE</th>
      <th style="width: 6%;">QTY</th>
      <th style="width: 12%; text-align: right;">WT/PC</th>
      <th style="width: 12%; text-align: right;">TOTAL WT</th>
      <th style="width: 16%; text-align: right;">PRICE/PC</th>
      <th style="width: 18%; text-align: right;">AMOUNT</th>
    </tr>
  `;
  
  // Discount HTML
  let discountHtml = '';
  if (totalItemDiscount > 0) {
    discountHtml = `
      <div class="summary-row discount-row">
        <span class="summary-label">Item Discounts (Total)</span>
        <span class="summary-value">- Rs. ${formatNumber(totalItemDiscount)}</span>
      </div>
    `;
  }
  
  // Packing HTML with type label
  const packingTypeLabel = getPackingLabel((quote as any).packing_type);
  const packingHtml = `
    <div class="summary-row">
      <span class="summary-label">Packing - ${packingTypeLabel}</span>
      <span class="summary-value">Rs. ${formatNumber(packing)}</span>
    </div>
  `;
  
  // Shipping/Freight HTML
  const shippingHtml = shipping > 0 ? `
    <div class="summary-row">
      <span class="summary-label">Freight Charges${quote.delivery_location ? ` (to ${quote.delivery_location})` : ''}</span>
      <span class="summary-value">Rs. ${formatNumber(shipping)}</span>
    </div>
  ` : '';
  
  // Customer details
  const customerCode = quote.customer_code || '';
  const customerCodeHtml = customerCode ? `<div class="customer-code">Customer Code: ${customerCode}</div>` : '';
  
  // Customer RFQ Reference
  const customerRfqNo = (quote as any).customer_rfq_no;
  const customerRfqNoHtml = customerRfqNo ? `<div class="customer-ref">Customer Ref: ${customerRfqNo}</div>` : '';
  
  // Address HTML
  let addressHtml = '';
  if (quote.customer_details?.address) {
    const parts = [quote.customer_details.address];
    if (quote.customer_details.city) parts.push(`<br>${quote.customer_details.city}`);
    if (quote.customer_details.state) parts.push(`, ${quote.customer_details.state}`);
    if (quote.customer_details.pincode) parts.push(` - ${quote.customer_details.pincode}`);
    addressHtml = `<div class="info-address">${parts.join('')}</div>`;
  }
  
  const gstHtml = quote.customer_details?.gst_number ? `<div class="info-gst">GSTIN: ${quote.customer_details.gst_number}</div>` : '';
  
  const contactParts = [];
  if (quote.customer_details?.phone) contactParts.push(`Ph: ${quote.customer_details.phone}`);
  if (quote.customer_details?.email) contactParts.push(quote.customer_details.email);
  const contactHtml = contactParts.length > 0 ? `<div class="info-contact">${contactParts.join(' | ')}</div>` : '';
  
  // Original RFQ reference
  const rfqRefHtml = quote.original_rfq_number ? `<div class="doc-ref">Ref: ${quote.original_rfq_number}</div>` : '';
  
  // Packing type labels
  const packingTypeLabels: { [key: string]: string } = {
    'standard': 'Standard (1%)',
    'pallet': 'Pallet (4%)',
    'wooden_box': 'Wooden Box (8%)'
  };
  
  // Get packing label with custom support
  const getPackingLabel = (type: string | undefined): string => {
    if (!type) return 'Standard (1%)';
    if (packingTypeLabels[type]) return packingTypeLabels[type];
    if (type.startsWith('custom_')) {
      const percent = type.split('_')[1] || '0';
      return `Custom (${percent}%)`;
    }
    return type;
  };
  
  // Packing & Delivery info for RFQ (shown even when prices hidden)
  const packingType = (quote as any).packing_type;
  let packingDeliveryHtml = '';
  if (packingType || quote.delivery_location) {
    let items = [];
    if (packingType) {
      const packingLabel = getPackingLabel(packingType);
      items.push(`<strong>Packing Type:</strong> ${packingLabel}`);
    }
    if (quote.delivery_location) {
      items.push(`<strong>Delivery Pincode:</strong> ${quote.delivery_location}`);
    }
    packingDeliveryHtml = `
      <div class="packing-delivery-box">
        ${items.join('<span class="separator">|</span>')}
      </div>
    `;
  }
  
  // Delivery location (detailed box)
  const deliveryHtml = quote.delivery_location ? `
    <div class="delivery-box">
      <strong>Delivery Location:</strong> PIN Code ${quote.delivery_location}
    </div>
  ` : '';
  
  // Notes
  const notesHtml = (quote as any).notes ? `
    <div class="delivery-box notes-box">
      <strong>Notes:</strong> ${(quote as any).notes}
    </div>
  ` : '';
  
  // RFQ Notice (shown when prices are hidden)
  const rfqNoticeHtml = shouldHidePrices ? `
    <div class="rfq-notice">
      <strong>This is a Request for Quotation</strong><br>
      <span style="color: #666; font-size: 10px;">Pricing will be provided upon review by our team. You will receive a formal quotation via email.</span>
    </div>
  ` : '';

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
          font-family: 'Segoe UI', Arial, sans-serif; 
          color: #1a1a1a; 
          font-size: 11px;
          line-height: 1.4;
          padding: 15px;
        }
        
        .header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding-bottom: 15px;
          border-bottom: 2px solid #960018;
          margin-bottom: 10px;
        }
        .logo {
          font-size: 26px;
          font-weight: 800;
          letter-spacing: -1px;
          color: #1a1a1a;
        }
        .logo span { color: #960018; }
        .company-tagline {
          font-size: 9px;
          color: #960018;
          letter-spacing: 2px;
          margin-top: 2px;
          font-style: italic;
        }
        .doc-type { text-align: right; }
        .doc-title {
          font-size: 18px;
          font-weight: 700;
          color: #960018;
          letter-spacing: 1px;
        }
        .doc-number {
          font-size: 13px;
          font-weight: 600;
          color: #333;
          margin-top: 3px;
        }
        .doc-date {
          font-size: 10px;
          color: #666;
          margin-top: 2px;
        }
        .doc-ref {
          font-size: 10px;
          color: #0066cc;
          margin-top: 2px;
          font-weight: 500;
        }
        
        .company-info-header {
          font-size: 8px;
          color: #666;
          text-align: center;
          margin-bottom: 8px;
          padding: 5px;
          background: #f9f9f9;
          border-radius: 3px;
        }
        
        .report-generated {
          font-size: 9px;
          color: #888;
          text-align: center;
          margin-bottom: 15px;
          font-style: italic;
        }
        
        .info-section {
          display: flex;
          gap: 20px;
          margin-bottom: 15px;
        }
        .info-box {
          flex: 1;
          padding: 12px;
          background: #f8f9fa;
          border-radius: 6px;
          border-left: 3px solid #960018;
        }
        .info-box-title {
          font-size: 9px;
          font-weight: 700;
          color: #960018;
          text-transform: uppercase;
          margin-bottom: 6px;
          letter-spacing: 0.5px;
        }
        .info-company {
          font-size: 12px;
          font-weight: 700;
          color: #1a1a1a;
          margin-bottom: 3px;
        }
        .info-address {
          font-size: 10px;
          color: #444;
          line-height: 1.4;
        }
        .info-contact {
          font-size: 9px;
          color: #666;
          margin-top: 4px;
        }
        .info-gst {
          font-size: 9px;
          color: #444;
          font-weight: 600;
          margin-top: 3px;
        }
        .customer-code {
          color: #960018;
          font-weight: bold;
          margin-bottom: 4px;
        }
        .customer-ref {
          color: #1565C0;
          font-weight: bold;
          margin-bottom: 4px;
        }
        
        .delivery-box {
          background: #e3f2fd;
          border-left: 3px solid #1976d2;
          padding: 10px;
          border-radius: 4px;
          margin-bottom: 10px;
          font-size: 10px;
        }
        .notes-box {
          background: #fff5f5;
          border-left: 3px solid #960018;
        }
        
        .packing-delivery-box {
          padding: 10px;
          background: #f5f5f5;
          border-radius: 4px;
          margin-bottom: 15px;
          font-size: 10px;
          display: flex;
          gap: 20px;
          flex-wrap: wrap;
        }
        .packing-delivery-box .separator {
          color: #ccc;
          margin: 0 10px;
        }
        
        .rfq-notice {
          padding: 15px;
          background: #FFF3CD;
          border: 1px solid #FFEEBA;
          border-radius: 8px;
          margin-top: 20px;
          margin-bottom: 20px;
          text-align: center;
        }
        
        .weight-footer-row {
          background: #e8f4fc !important;
          font-weight: bold;
        }
        .weight-footer-row td {
          color: #0066cc;
          padding: 8px 10px;
        }
        
        .section-title {
          font-size: 11px;
          font-weight: 700;
          color: #960018;
          margin-bottom: 8px;
          padding-bottom: 4px;
          border-bottom: 1px solid #e5e5e5;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 15px;
          font-size: 10px;
        }
        th {
          background: #960018;
          color: white;
          padding: 8px 6px;
          text-align: center;
          font-weight: 600;
          font-size: 9px;
        }
        td {
          padding: 8px 6px;
          border-bottom: 1px solid #e5e5e5;
        }
        tr:nth-child(even) { background: #fafafa; }
        .cell-center { text-align: center; }
        .cell-right { text-align: right; }
        .cell-left { text-align: left; }
        
        .product-name {
          font-weight: 600;
          color: #1a1a1a;
          font-size: 10px;
        }
        .product-specs {
          font-size: 8px;
          color: #666;
          margin-top: 2px;
        }
        .product-remark {
          font-size: 8px;
          color: #0066cc;
          font-style: italic;
          margin-top: 2px;
        }
        
        .weight-section {
          background: #fff3cd;
          border: 1px solid #ffc107;
          border-radius: 6px;
          padding: 10px;
          margin-bottom: 15px;
        }
        .weight-title {
          font-weight: 700;
          color: #856404;
          margin-bottom: 5px;
        }
        .weight-value {
          font-size: 14px;
          font-weight: 700;
          color: #856404;
        }
        
        .summary-section {
          display: flex;
          justify-content: flex-end;
          margin-bottom: 15px;
        }
        .summary-box {
          width: 300px;
          background: #f8f9fa;
          border-radius: 6px;
          padding: 12px;
          border: 1px solid #e5e5e5;
        }
        .summary-row {
          display: flex;
          justify-content: space-between;
          padding: 6px 0;
          font-size: 10px;
          border-bottom: 1px solid #eee;
        }
        .summary-row:last-child {
          border-bottom: none;
        }
        .discount-row {
          color: #22C55E;
        }
        .summary-label {
          color: #666;
        }
        .summary-value {
          font-weight: 600;
          color: #1a1a1a;
        }
        .summary-row.grand {
          border-top: 2px solid #960018;
          margin-top: 6px;
          padding-top: 10px;
          font-size: 14px;
          font-weight: 700;
        }
        .summary-row.grand .summary-label,
        .summary-row.grand .summary-value {
          color: #960018;
          font-weight: 700;
        }
        
        .terms-container {
          margin-top: 15px;
          border-top: 1px solid #e5e5e5;
          padding-top: 15px;
        }
        .terms-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .term-item {
          padding: 8px;
          background: #f8f9fa;
          border-radius: 4px;
          border-left: 2px solid #960018;
        }
        .term-item-title {
          font-size: 9px;
          font-weight: 700;
          color: #960018;
          margin-bottom: 3px;
        }
        .term-item-text {
          font-size: 8px;
          color: #444;
          line-height: 1.3;
        }
        
        .footer {
          margin-top: 20px;
          padding-top: 15px;
          border-top: 2px solid #960018;
          display: flex;
          justify-content: space-between;
        }
        .footer-company {
          font-size: 12px;
          font-weight: 700;
          color: #1a1a1a;
        }
        .footer-tagline {
          font-size: 8px;
          color: #960018;
          font-style: italic;
        }
        .footer-signature {
          text-align: center;
          font-size: 10px;
          color: #666;
          border-top: 1px solid #333;
          padding-top: 5px;
          margin-top: 40px;
          width: 150px;
        }
        .footer-note {
          text-align: center;
          font-size: 8px;
          color: #999;
          margin-top: 15px;
          font-style: italic;
        }
        
        @media print {
          body { padding: 10px; }
          .terms-container { page-break-before: auto; }
        }
      </style>
    </head>
    <body>
      <!-- Header -->
      <div class="header">
        <div class="logo-section">
          <div class="logo">C<span>O</span>NVER<span>O</span></div>
          <div class="company-tagline">Rolling towards the future</div>
        </div>
        <div class="doc-type">
          <div class="doc-title">${pdfDocLabelFull}</div>
          <div class="doc-number">${quote.quote_number || `#${quote.id.slice(-6).toUpperCase()}`}</div>
          ${rfqRefHtml}
          <div class="doc-date">${displayDate}</div>
        </div>
      </div>
      
      <div class="company-info-header">
        <span>Plot No. 39, Swapnil Industrial Park, Beside Shiv Aaradhna Estate, Ahmedabad-Indore Highway, Village-Kuha, Ahmedabad, Gujarat 382433</span>
        <span>|</span>
        <span>info@convero.in</span>
        <span>|</span>
        <span>www.convero.in</span>
        <span>|</span>
        <span>GSTIN: 24BAUPP4310D2ZT</span>
      </div>
      
      <div class="report-generated">
        Report Generated: ${reportGenerated}
      </div>

      <!-- Info Section -->
      <div class="info-section">
        <div class="info-box">
          <div class="info-box-title">From</div>
          <div class="info-company">CONVERO SOLUTIONS</div>
          <div style="font-size: 9px; color: #960018; font-style: italic; margin-bottom: 4px;">Rolling towards the future</div>
          <div class="info-address">
            Plot No. 39, Swapnil Industrial Park,<br>
            Beside Shiv Aaradhna Estate,<br>
            Ahmedabad-Indore Highway,<br>
            Village-Kuha, Ahmedabad,<br>
            Gujarat 382433
          </div>
          <div class="info-contact">
            <strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in
          </div>
          <div class="info-contact" style="margin-top: 3px;">
            <strong>GSTIN:</strong> 24BAUPP4310D2ZT
          </div>
        </div>
        <div class="info-box">
          <div class="info-box-title">Bill To</div>
          ${customerCodeHtml}
          ${customerRfqNoHtml}
          <div class="info-company">${quote.customer_company || quote.customer_details?.company || quote.customer_details?.name || quote.customer_name}</div>
          ${addressHtml}
          ${gstHtml}
          ${contactHtml}
        </div>
      </div>
      
      ${deliveryHtml}
      ${notesHtml}
      ${packingDeliveryHtml}

      <!-- Products Table -->
      <div class="section-title">${shouldHidePrices ? 'Products Requested' : 'Product Details'}</div>
      <table>
        <thead>
          ${tableHeader}
        </thead>
        <tbody>
          ${productsHtml}
        </tbody>
        ${shouldHidePrices ? `
        <tfoot>
          <tr class="weight-footer-row">
            <td colspan="4" style="text-align: right;">Grand Total Weight:</td>
            <td style="text-align: right;">${grandTotalWeight.toFixed(2)} kg</td>
          </tr>
        </tfoot>
        ` : ''}
      </table>
      
      ${shouldHidePrices ? `
        ${rfqNoticeHtml}
      ` : `
        <!-- Weight Section -->
        <div class="weight-section">
          <div class="weight-title">Total Estimated Weight</div>
          <div class="weight-value">${grandTotalWeight.toFixed(2)} kg</div>
        </div>
        
        <!-- Summary/Totals -->
        <div class="summary-section">
          <div class="summary-box">
            <div class="summary-row">
              <span class="summary-label">Subtotal (after discounts)</span>
              <span class="summary-value">Rs. ${formatNumber(subtotalAfterDiscount)}</span>
            </div>
            ${discountHtml}
            ${packingHtml}
            ${shippingHtml}
            <div class="summary-row">
              <span class="summary-label">Taxable Amount</span>
              <span class="summary-value">Rs. ${formatNumber(taxableAmount)}</span>
            </div>
            <div class="summary-row">
              <span class="summary-label">CGST (9%)</span>
              <span class="summary-value">Rs. ${formatNumber(cgst)}</span>
            </div>
            <div class="summary-row">
              <span class="summary-label">SGST (9%)</span>
              <span class="summary-value">Rs. ${formatNumber(sgst)}</span>
            </div>
            <div class="summary-row grand">
              <span class="summary-label">GRAND TOTAL</span>
              <span class="summary-value">Rs. ${formatNumber(grandTotal)}</span>
            </div>
          </div>
        </div>
      `}

      <!-- Terms and Conditions -->
      <div class="terms-container">
        <div class="section-title">Terms & Conditions</div>
        <div class="terms-grid">
          <div class="term-item">
            <div class="term-item-title">Payment Terms</div>
            <div class="term-item-text">100% advance along with PO. GST @18% extra as applicable.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Delivery</div>
            <div class="term-item-text">Ex-works Ahmedabad. Transit insurance by buyer.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Validity</div>
            <div class="term-item-text">This quotation is valid for 15 days from the date of issue.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Lead Time</div>
            <div class="term-item-text">3-4 weeks from the date of PO & advance receipt.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Warranty</div>
            <div class="term-item-text">12 months from date of supply against manufacturing defects.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Standards</div>
            <div class="term-item-text">IS-8598 (Idlers for belt conveyors)</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Painting</div>
            <div class="term-item-text">One coat black synthetic enamel (40 microns). Rust preventive coating on machined parts.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">Packing</div>
            <div class="term-item-text">As per selection made in the application.</div>
          </div>
          <div class="term-item">
            <div class="term-item-title">TIR (Total Indicated Runout)</div>
            <div class="term-item-text">Shall not exceed 1.6 mm as per IS-8598.</div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="footer">
        <div class="footer-left">
          <div class="footer-company">CONVERO SOLUTIONS</div>
          <div class="footer-tagline">Rolling towards the future</div>
          <div style="font-size: 8px; margin-top: 3px;">Plot No. 39, Swapnil Industrial Park,</div>
          <div style="font-size: 8px;">Beside Shiv Aaradhna Estate, Ahmedabad-Indore Highway,</div>
          <div style="font-size: 8px;">Village-Kuha, Ahmedabad, Gujarat 382433</div>
          <div style="font-size: 8px; margin-top: 5px;"><strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in</div>
          <div style="font-size: 8px;"><strong>GSTIN:</strong> 24BAUPP4310D2ZT</div>
        </div>
        <div class="footer-right">
          <div class="footer-signature">Authorized Signature</div>
        </div>
      </div>
      
      <div class="footer-note">
        This is a computer-generated document. Generated on ${reportGenerated}
      </div>
    </body>
    </html>
  `;
};
