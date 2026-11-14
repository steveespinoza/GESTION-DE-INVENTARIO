ALTER TABLE movements DROP CONSTRAINT movements_kind_check;
ALTER TABLE movements ADD CONSTRAINT movements_kind_check
    CHECK (kind IN ('receipt', 'opening', 'issue', 'transfer'));
