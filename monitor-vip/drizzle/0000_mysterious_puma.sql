CREATE TABLE `counters` (
	`key` text PRIMARY KEY NOT NULL,
	`value` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `document_jobs` (
	`process_id` text PRIMARY KEY NOT NULL,
	`status` text NOT NULL,
	`requested_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`payload_json` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `documents` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`process_id` text NOT NULL,
	`label` text NOT NULL,
	`object_key` text NOT NULL,
	`sha256` text DEFAULT '' NOT NULL,
	`document_type` text DEFAULT '' NOT NULL,
	`reading_status` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `outreach` (
	`process_id` text PRIMARY KEY NOT NULL,
	`status` text DEFAULT 'NAO_INICIADO' NOT NULL,
	`decision_maker` text DEFAULT '' NOT NULL,
	`email` text DEFAULT '' NOT NULL,
	`phone` text DEFAULT '' NOT NULL,
	`last_contact_at` text DEFAULT '' NOT NULL,
	`sent_at` text DEFAULT '' NOT NULL,
	`next_follow_up_at` text DEFAULT '' NOT NULL,
	`subject` text DEFAULT '' NOT NULL,
	`body` text DEFAULT '' NOT NULL,
	`notes` text DEFAULT '' NOT NULL,
	`operator` text DEFAULT 'Ana Fonseca' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `outreach_history` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`process_id` text NOT NULL,
	`at` text NOT NULL,
	`event` text NOT NULL,
	`fields_json` text NOT NULL,
	`status` text NOT NULL,
	`operator` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `proposals` (
	`number` text PRIMARY KEY NOT NULL,
	`created_at` text NOT NULL,
	`status` text NOT NULL,
	`process_id` text NOT NULL,
	`supplier` text NOT NULL,
	`supplier_cnpj` text DEFAULT '' NOT NULL,
	`agency` text DEFAULT '' NOT NULL,
	`tender` text DEFAULT '' NOT NULL,
	`administrative_process` text DEFAULT '' NOT NULL,
	`decision_maker` text DEFAULT '' NOT NULL,
	`contract_value` real NOT NULL,
	`guarantee_percentage` real NOT NULL,
	`insured_amount` real NOT NULL,
	`annual_rate` real NOT NULL,
	`term_months` integer NOT NULL,
	`estimated_premium` real NOT NULL,
	`notes` text DEFAULT '' NOT NULL,
	`operator` text DEFAULT 'Ana Fonseca' NOT NULL
);
