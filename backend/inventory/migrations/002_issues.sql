ALTER TABLE movements DROP CONSTRAINT movements_kind_check;
ALTER TABLE movements ADD CONSTRAINT movements_kind_check
    CHECK (kind IN ('receipt', 'opening', 'issue'));

ALTER TABLE movement_details DROP CONSTRAINT movement_details_quantity_check;
ALTER TABLE movement_details ADD CONSTRAINT movement_details_quantity_check
    CHECK (quantity <> 0 AND quantity <> 'NaN');
