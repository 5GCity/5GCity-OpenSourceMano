--
-- Tear down database structure required for integrating OSM with
-- Wide Are Network Infrastructure Managers
--

DROP TABLE IF EXISTS wim_port_mappings;
DROP TABLE IF EXISTS wim_nfvo_tenants;
DROP TABLE IF EXISTS instance_wim_nets;

ALTER TABLE `vim_wim_actions` DROP FOREIGN KEY `FK_actions_wims`;
ALTER TABLE `vim_wim_actions` DROP INDEX `FK_actions_wims`;
ALTER TABLE `vim_wim_actions` DROP INDEX `item_type_id`;
ALTER TABLE `vim_wim_actions` MODIFY `item` enum(
  'datacenters_flavors',
  'datacenter_images',
  'instance_nets',
  'instance_vms',
  'instance_interfaces',
  'instance_sfis',
  'instance_sfs',
  'instance_classifications',
  'instance_sfps') NOT NULL
  COMMENT 'table where the item is stored';
ALTER TABLE `vim_wim_actions` MODIFY `datacenter_vim_id` varchar(36) NOT NULL;
ALTER TABLE `vim_wim_actions` DROP `wim_internal_id`, DROP `wim_account_id`;
ALTER TABLE `vim_wim_actions` RENAME TO `vim_actions`;

DROP TABLE IF EXISTS wim_accounts;
DROP TABLE IF EXISTS wims;

DELETE FROM schema_version WHERE version_int='34';
