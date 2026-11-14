CREATE TABLE users (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'operator'))
);

CREATE TABLE locations (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE user_locations (
    user_id integer NOT NULL REFERENCES users,
    location_id integer NOT NULL REFERENCES locations,
    PRIMARY KEY (user_id, location_id)
);

CREATE TABLE products (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku text NOT NULL UNIQUE,
    name text NOT NULL,
    unit text NOT NULL,
    category text NOT NULL
);

CREATE TABLE stock (
    product_id integer NOT NULL REFERENCES products,
    location_id integer NOT NULL REFERENCES locations,
    quantity numeric(18, 3) NOT NULL CHECK (quantity >= 0 AND quantity <> 'NaN'),
    PRIMARY KEY (product_id, location_id)
);

CREATE TABLE movements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('receipt', 'opening')),
    actor_id integer NOT NULL REFERENCES users,
    movement_date date NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    reference text CHECK (length(reference) <= 120)
);

CREATE TABLE movement_details (
    movement_id bigint NOT NULL REFERENCES movements,
    product_id integer NOT NULL REFERENCES products,
    location_id integer NOT NULL REFERENCES locations,
    quantity numeric(18, 3) NOT NULL CHECK (quantity > 0 AND quantity <> 'NaN'),
    PRIMARY KEY (movement_id, product_id, location_id)
);

CREATE INDEX movement_details_location_idx
    ON movement_details (location_id, movement_id DESC);
