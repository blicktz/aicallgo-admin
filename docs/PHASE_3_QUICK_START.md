# Phase 3 Quick Start Guide

This guide will help you test the newly implemented Phase 3 features for the admin board.

## What Was Implemented

Phase 3 adds critical admin capabilities for managing user entitlements and credits:

1. **Feature Entitlement Management** (`pages/6_⚡_Entitlements.py`)
   - Grant/revoke feature access to users
   - View plan-based features and overrides
   - Set expiration dates on overrides
   - Delete overrides to revert to plan defaults
   - Full audit trail in notes field

2. **Credit Adjustment** (`pages/7_💰_Credits.py`)
   - View user credit balance breakdown
   - View transaction history
   - Adjust credits (add/deduct)
   - Preview adjustments before applying
   - Large amount and negative balance warnings
   - Full audit trail in transaction metadata

3. **Supporting Services**
   - `services/audit_service.py` - Audit logging
   - `services/entitlement_service.py` - Entitlement operations
   - `services/credit_service.py` - Credit operations

## Prerequisites

Before testing Phase 3, ensure:

1. **Phase 1 & 2 are working**
   - Authentication is functional
   - Database connection is established
   - Basic pages (Dashboard, Users, Businesses, etc.) are accessible

2. **Database Access**
   - Port-forward to staging database is running:
     ```bash
     export KUBECONFIG=~/staging-kubeconfig.txt
     kubectl port-forward svc/postgres 5432:5432 -n aicallgo-staging
     ```

3. **Environment Setup**
   - `.streamlit/secrets.toml` has `ADMIN_USERNAME` set
   - Database connection string is configured

## Testing Entitlements Page

### Access the Page

1. Start the admin board:
   ```bash
   cd services/admin-board
   streamlit run app.py
   ```

2. Navigate to **⚡ Entitlements** in the sidebar

### Test Cases

#### TC1: View User Entitlements

1. Search for a user by email in the left panel
2. Click on a user row to select them
3. Verify the right panel shows:
   - Current plan and plan features
   - Active overrides (if any)
   - Computed access table

**Expected**: User's entitlement data loads without errors

#### TC2: Grant Feature Access

1. Select a user
2. Scroll to "Grant/Revoke Feature Access" form
3. Select a feature from the dropdown
4. Choose "Grant" access
5. Optionally set an expiration date
6. Enter notes (minimum 10 characters): "Testing feature grant for demo purposes"
7. Expand the preview to verify changes
8. Click "Save Override"
9. Click "✅ Confirm Override"

**Expected**:
- Success message appears
- Page refreshes automatically
- Override appears in "Active Overrides" section
- Computed access table updates

#### TC3: Revoke Feature Access

1. Select a user
2. In the form, select a feature
3. Choose "Deny" access
4. Enter notes: "Testing feature revocation for demo"
5. Click "Save Override" and confirm

**Expected**:
- Success message appears
- Override appears with "🔴 Deny" badge
- Computed access shows feature as denied

#### TC4: Delete Override

1. Select a user with active overrides
2. Find an override in "Active Overrides"
3. Click "Delete" button
4. Enter deletion reason (min 10 chars): "Reverting to plan default"
5. Click "✅ Confirm"

**Expected**:
- Success message appears
- Override removed from list
- Computed access reverts to plan default

#### TC5: Validation Tests

Test these validation scenarios:

1. **Short notes**: Enter < 10 characters
   - Expected: Error message "Notes must be at least 10 characters"

2. **Past expiration date**: Try to set expiration in the past
   - Expected: Date picker prevents past dates

3. **Inactive user**: Select an inactive user
   - Expected: Error when trying to create override

## Testing Credits Page

### Access the Page

1. Navigate to **💰 Credits** in the sidebar

### Test Cases

#### TC6: View Credit Balance

1. Search for a user by email
2. Click on a user row to select them
3. Verify the right panel shows:
   - Total balance
   - Last updated timestamp
   - Balance breakdown (trial, subscription, credit pack, adjustments)
   - Transaction history table

**Expected**: Credit data loads without errors

#### TC7: Add Credits (Positive Adjustment)

1. Select a user
2. Scroll to "Adjust Credits" form
3. Enter amount: `10.00`
4. Select transaction type: "Adjustment"
5. Enter reason: "Testing credit addition for demo purposes"
6. Expand preview to verify:
   - Current balance
   - Adjustment amount (+$10.00)
   - New balance
7. Click "Apply Adjustment"

**Expected**:
- Success message appears
- Page refreshes
- Balance increases by $10.00
- New transaction appears in history with positive amount

#### TC8: Deduct Credits (Negative Adjustment)

1. Select a user
2. Enter amount: `-5.00`
3. Select transaction type: "Adjustment"
4. Enter reason: "Testing credit deduction for demo"
5. Click "Apply Adjustment"

**Expected**:
- Success message appears
- Balance decreases by $5.00
- New transaction appears with negative amount

#### TC9: Large Amount Warning

1. Select a user
2. Enter amount: `150.00` (> $100)
3. Enter reason: "Testing large amount warning"
4. Click "Apply Adjustment"

**Expected**:
- Warning appears: "⚠️ Confirm large adjustment: $150.00"
- Must click "✅ Confirm Large Adjustment" to proceed

#### TC10: Negative Balance Warning

1. Select a user with low balance (< $10)
2. Enter negative amount that will result in negative balance
3. Enter reason: "Testing negative balance warning"
4. Click "Apply Adjustment"

**Expected**:
- Error appears: "⚠️ This will create negative balance: -$X.XX"
- Must click "✅ Confirm Negative Balance" to proceed

#### TC11: Validation Tests

Test these validation scenarios:

1. **Zero amount**: Enter `0.00`
   - Expected: Error "Amount must be non-zero"

2. **Short reason**: Enter < 10 characters
   - Expected: Error "Reason must be at least 10 characters"

3. **Very large amount**: Enter `15000.00`
   - Expected: Error "Adjustment amount exceeds maximum allowed ($10,000)"

#### TC12: Transaction History Filtering

1. Select a user with multiple transactions
2. Change "Transaction Type" filter to specific types:
   - "grant_trial"
   - "deduct_usage"
   - "adjustment"
3. Verify table updates with filtered results

**Expected**: Only transactions of selected type appear

#### TC13: Refund Transaction

1. Select a user
2. Enter amount: `25.00`
3. Select transaction type: "Refund"
4. Enter reason: "Testing refund transaction for demo"
5. Click "Apply Adjustment"

**Expected**:
- Success message appears
- Transaction appears with type "Refund"

## Audit Trail Verification

### Check Entitlement Audit Trail

1. After creating an override, view it in "Active Overrides"
2. Click "View notes" expander
3. Verify notes contain:
   - `[ADMIN: {username} @ {timestamp}]` prefix
   - Your entered notes
   - ISO timestamp

### Check Credit Audit Trail

1. Use database tools or web-backend API to query:
   ```sql
   SELECT transaction_metadata
   FROM credit_transactions
   WHERE user_id = 'USER_ID'
   ORDER BY created_at DESC
   LIMIT 1;
   ```

2. Verify metadata JSON contains:
   - `admin_username`: Your admin username
   - `admin_reason`: Your entered reason
   - `adjustment_type`: "manual_admin"
   - `source`: "admin_board"
   - `timestamp`: ISO timestamp

## Transaction Safety Verification

### Test Rollback on Error

1. **Manual Test**: Temporarily break database connection
   - Stop port-forward: `Ctrl+C` on kubectl port-forward
   - Try to create an override or adjustment
   - Expected: Error message, no partial updates

2. **Check Database State**: After error, verify:
   - No new overrides created
   - No new transactions created
   - No balance updates
   - Database state unchanged

## Common Issues and Solutions

### Issue: "User not found" error

**Solution**:
- Verify user ID is correct
- Ensure user is active
- Check database connection

### Issue: "Feature not found" error

**Solution**:
- Verify feature exists in database
- Check `app/core/startup.py` in web-backend for valid feature keys
- Run web-backend migrations if features are missing

### Issue: Transaction rollback without clear error

**Solution**:
- Check admin board logs in terminal
- Look for `IntegrityError` or constraint violations
- Verify unique constraints (e.g., one override per user-feature pair)

### Issue: Audit trail not showing

**Solution**:
- Verify `ADMIN_USERNAME` is set in `.streamlit/secrets.toml`
- Check logs for audit service errors

### Issue: Page doesn't refresh after mutation

**Solution**:
- Clear Streamlit cache manually: Click "🔄 Refresh"
- Check browser console for JavaScript errors
- Restart Streamlit if needed

## Performance Expectations

All operations should complete within:

- **User search**: < 500ms
- **Load entitlements**: < 1 second
- **Load credit balance**: < 500ms
- **Create override**: < 2 seconds
- **Adjust credits**: < 2 seconds
- **Page refresh**: < 2 seconds

If operations are slower, check:
- Database connection latency
- Port-forward stability
- Query complexity

## Next Steps

After successfully testing Phase 3:

1. **Report Issues**: Document any bugs or unexpected behavior
2. **User Acceptance Testing**: Have team members test workflows
3. **Phase 4**: Move on to implementing:
   - Promotion tracking
   - Appointment viewing
   - System monitoring
   - CSV exports
   - Enhanced refresh capabilities

## Support

For issues or questions:
- Check logs in terminal running Streamlit
- Review Phase 3 implementation plan: `docs/PHASE_3_IMPLEMENTATION_PLAN.md`
- Check web-backend models and CRUD operations
- Verify database schema matches expectations
