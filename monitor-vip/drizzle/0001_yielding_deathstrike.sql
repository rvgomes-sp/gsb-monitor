CREATE TABLE `feed_metadata` (
	`id` integer PRIMARY KEY NOT NULL,
	`payload_json` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `opportunities` (
	`id` text PRIMARY KEY NOT NULL,
	`position` integer NOT NULL,
	`process_id` text NOT NULL,
	`supplier_cnpj` text NOT NULL,
	`route` text NOT NULL,
	`contract_value` real NOT NULL,
	`payload_json` text NOT NULL,
	`updated_at` text NOT NULL
);
