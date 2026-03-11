// PDF HTML generation for quotes
import { Quote } from './types';
import { formatDate } from './utils';

interface GeneratePdfOptions {
  isCustomer: boolean;
}

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
  
  // ALWAYS use item-level discount format for PDF display
  const useItemDiscounts = true;
  
  // Calculate totals with item discounts
  let calculatedSubtotal = 0;
  let totalItemDiscount = 0;
  
  const productsHtml = quote.products.map((product, index) => {
    const hasItemDiscounts = quote.use_item_discounts && product.item_discount_percent !== undefined;
    let itemDiscountPercent = 0;
    
    if (hasItemDiscounts) {
      itemDiscountPercent = product.item_discount_percent || 0;
    } else if (quote.total_discount > 0 && quote.subtotal > 0) {
      itemDiscountPercent = (quote.total_discount / quote.subtotal) * 100;
    }
    
    const valueAfterDiscount = product.unit_price * (1 - itemDiscountPercent / 100);
    const lineTotal = product.quantity * valueAfterDiscount;
    const originalAmount = product.quantity * product.unit_price;
    const itemDiscountAmount = originalAmount - lineTotal;
    
    calculatedSubtotal += lineTotal;
    totalItemDiscount += itemDiscountAmount;
    
    // Get weight info from specifications
    const weightKg = product.specifications?.weight_kg || 0;
    const totalWeight = (weightKg * product.quantity).toFixed(2);
    
    if (shouldHidePrices) {
      return `
        <tr>
          <td class="cell-center">${index + 1}</td>
          <td class="cell-left">
            <div class="product-name">${product.product_id}</div>
            ${product.specifications ? `
              <div class="product-specs">
                ${product.specifications.roller_type ? `Type: ${product.specifications.roller_type}` : ''}
                ${product.specifications.pipe_diameter ? ` | Pipe: ${product.specifications.pipe_diameter}mm` : ''}
                ${product.specifications.shaft_diameter ? ` | Shaft: ${product.specifications.shaft_diameter}mm` : ''}
                ${product.specifications.bearing ? ` | Bearing: ${product.specifications.bearing}` : ''}
              </div>
            ` : ''}
            ${product.remark ? `<div class="product-remark">Note: ${product.remark}</div>` : ''}
          </td>
          <td class="cell-center">${product.quantity}</td>
        </tr>
      `;
    }
    
    return `
      <tr>
        <td class="cell-center">${index + 1}</td>
        <td class="cell-left">
          <div class="product-name">${product.product_id}</div>
          ${product.specifications ? `
            <div class="product-specs">
              ${product.specifications.roller_type ? `Type: ${product.specifications.roller_type}` : ''}
              ${product.specifications.pipe_diameter ? ` | Pipe: ${product.specifications.pipe_diameter}mm` : ''}
              ${product.specifications.shaft_diameter ? ` | Shaft: ${product.specifications.shaft_diameter}mm` : ''}
              ${product.specifications.bearing ? ` | Bearing: ${product.specifications.bearing}` : ''}
              ${weightKg > 0 ? ` | Unit Wt: ${weightKg.toFixed(2)}kg` : ''}
            </div>
          ` : ''}
          ${product.remark ? `<div class="product-remark">Note: ${product.remark}</div>` : ''}
        </td>
        <td class="cell-center">${product.quantity}</td>
        <td class="cell-right">Rs. ${product.unit_price?.toFixed(2)}</td>
        <td class="cell-center">${itemDiscountPercent.toFixed(1)}%</td>
        <td class="cell-right">Rs. ${valueAfterDiscount.toFixed(2)}</td>
        <td class="cell-right"><strong>Rs. ${lineTotal.toFixed(2)}</strong></td>
      </tr>
    `;
  }).join('');

  // Calculate totals
  const subtotalAfterDiscount = useItemDiscounts ? calculatedSubtotal : ((quote.subtotal || 0) - (quote.total_discount || 0));
  const taxableAmount = subtotalAfterDiscount + (quote.packing_charges || 0);
  const cgst = taxableAmount * 0.09;
  const sgst = taxableAmount * 0.09;
  const grandTotal = (taxableAmount + (quote.shipping_cost || 0)) * 1.18;
  
  // Calculate total weight
  const totalWeight = quote.products.reduce((sum, p) => {
    const wt = p.specifications?.weight_kg || 0;
    return sum + (wt * p.quantity);
  }, 0);
  
  // Dynamic table header
  const tableHeader = shouldHidePrices ? `
    <tr>
      <th style="width: 8%;">SR.</th>
      <th style="width: 72%; text-align: left;">ITEM CODE / DESCRIPTION</th>
      <th style="width: 20%;">QTY</th>
    </tr>
  ` : `
    <tr>
      <th style="width: 5%;">SR.</th>
      <th style="width: 25%; text-align: left;">ITEM CODE</th>
      <th style="width: 8%;">QTY</th>
      <th style="width: 15%; text-align: right;">RATE</th>
      <th style="width: 12%;">DISC %</th>
      <th style="width: 17%; text-align: right;">VALUE AFTER DISC</th>
      <th style="width: 18%; text-align: right;">TOTAL</th>
    </tr>
  `;

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
          margin-bottom: 15px;
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
          margin-bottom: 10px;
          padding: 5px;
          background: #f9f9f9;
          border-radius: 3px;
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
        
        .totals-section {
          display: flex;
          justify-content: flex-end;
          margin-bottom: 15px;
        }
        .totals-box {
          width: 280px;
          background: #f8f9fa;
          border-radius: 6px;
          padding: 12px;
          border: 1px solid #e5e5e5;
        }
        .total-row {
          display: flex;
          justify-content: space-between;
          padding: 4px 0;
          font-size: 10px;
        }
        .total-row.grand {
          border-top: 2px solid #960018;
          margin-top: 6px;
          padding-top: 8px;
          font-size: 13px;
          font-weight: 700;
          color: #960018;
        }
        .total-label { color: #666; }
        .total-value { font-weight: 600; color: #1a1a1a; }
        
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
        .footer-signature {
          text-align: center;
          font-size: 10px;
          color: #666;
          border-top: 1px solid #333;
          padding-top: 5px;
          margin-top: 40px;
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
          ${quote.original_rfq_number ? `<div class="doc-ref">Ref: ${quote.original_rfq_number}</div>` : ''}
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
          ${quote.customer_code ? `<div class="customer-code" style="color: #960018; font-weight: bold; margin-bottom: 4px;">Customer Code: ${quote.customer_code}</div>` : ''}
          <div class="info-company">${quote.customer_company || quote.customer_details?.company || quote.customer_details?.name || quote.customer_name}</div>
          ${quote.customer_details?.address ? `
            <div class="info-address">
              ${quote.customer_details.address}${quote.customer_details.city ? `<br>${quote.customer_details.city}` : ''}${quote.customer_details.state ? `, ${quote.customer_details.state}` : ''}${quote.customer_details.pincode ? ` - ${quote.customer_details.pincode}` : ''}
            </div>
          ` : ''}
          ${quote.customer_details?.gst_number ? `
            <div class="info-gst">GSTIN: ${quote.customer_details.gst_number}</div>
          ` : ''}
          ${quote.customer_details?.phone || quote.customer_details?.email ? `
            <div class="info-contact">
              ${quote.customer_details.phone ? `Ph: ${quote.customer_details.phone}` : ''}
              ${quote.customer_details.phone && quote.customer_details.email ? ' | ' : ''}
              ${quote.customer_details.email || ''}
            </div>
          ` : ''}
        </div>
      </div>

      <!-- Products Table -->
      <div class="section-title">Product Details</div>
      <table>
        <thead>
          ${tableHeader}
        </thead>
        <tbody>
          ${productsHtml}
        </tbody>
      </table>
      
      ${!shouldHidePrices ? `
        <!-- Weight Section -->
        <div class="weight-section">
          <div class="weight-title">Total Estimated Weight</div>
          <div class="weight-value">${totalWeight.toFixed(2)} kg</div>
        </div>
        
        <!-- Totals -->
        <div class="totals-section">
          <div class="totals-box">
            <div class="total-row">
              <span class="total-label">Subtotal (after item discounts)</span>
              <span class="total-value">Rs. ${subtotalAfterDiscount.toFixed(2)}</span>
            </div>
            ${(quote.packing_charges || 0) > 0 ? `
              <div class="total-row">
                <span class="total-label">Packing (${quote.packing_type || 'Standard'})</span>
                <span class="total-value">Rs. ${(quote.packing_charges || 0).toFixed(2)}</span>
              </div>
            ` : ''}
            ${(quote.shipping_cost || 0) > 0 ? `
              <div class="total-row">
                <span class="total-label">Freight${quote.delivery_location ? ` (to ${quote.delivery_location})` : ''}</span>
                <span class="total-value">Rs. ${(quote.shipping_cost || 0).toFixed(2)}</span>
              </div>
            ` : ''}
            <div class="total-row">
              <span class="total-label">Taxable Amount</span>
              <span class="total-value">Rs. ${(taxableAmount + (quote.shipping_cost || 0)).toFixed(2)}</span>
            </div>
            <div class="total-row">
              <span class="total-label">CGST (9%)</span>
              <span class="total-value">Rs. ${((taxableAmount + (quote.shipping_cost || 0)) * 0.09).toFixed(2)}</span>
            </div>
            <div class="total-row">
              <span class="total-label">SGST (9%)</span>
              <span class="total-value">Rs. ${((taxableAmount + (quote.shipping_cost || 0)) * 0.09).toFixed(2)}</span>
            </div>
            <div class="total-row grand">
              <span>GRAND TOTAL</span>
              <span>Rs. ${grandTotal.toFixed(2)}</span>
            </div>
          </div>
        </div>
      ` : ''}

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
          <div style="font-size: 8px; color: #960018; font-style: italic;">Rolling towards the future</div>
          <div style="font-size: 8px; margin-top: 3px;">Plot No. 39, Swapnil Industrial Park, Village-Kuha, Ahmedabad, Gujarat 382433</div>
          <div style="font-size: 8px;"><strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in | <strong>GSTIN:</strong> 24BAUPP4310D2ZT</div>
        </div>
        <div class="footer-right">
          <div style="height: 40px;"></div>
          <div class="footer-signature">Authorized Signatory</div>
        </div>
      </div>
      
      <div class="footer-note">
        This is a computer-generated quotation. E&OE (Errors and Omissions Excepted)
      </div>
    </body>
    </html>
  `;
};
