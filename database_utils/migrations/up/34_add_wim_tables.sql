--
-- Setup database structure required for integrating OSM with
-- Wide Are Network Infrastructure Managers
--

DROP TABLE IF EXISTS wims;
CREATE TABLE wims (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `type` varchar(36) NOT NULL DEFAULT 'odl',
  `wim_url` varchar(150) NOT NULL,
  `config` varchar(4000) DEFAULT NULL,
  `created_at` double NOT NULL,
  `modified_at` double DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `name` (`name`)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT
COMMENT='WIMs managed by the NFVO.';

DROP TABLE IF EXISTS wim_accounts;
CREATE TABLE wim_accounts (
  `uuid` varchar(36) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `wim_id` varchar(36) NOT NULL,
  `created` enum('true','false') NOT NULL DEFAULT 'false',
  `user` varchar(64) DEFAULT NULL,
  `password` varchar(64) DEFAULT NULL,
  `config` varchar(4000) DEFAULT NULL,
  `created_at` double NOT NULL,
  `modified_at` double DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `wim_name` (`wim_id`,`name`),
  KEY `FK_wim_accounts_wims` (`wim_id`),
  CONSTRAINT `FK_wim_accounts_wims` FOREIGN KEY (`wim_id`)
    REFERENCES `wims` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT
COMMENT='WIM accounts by the user';

DROP TABLE IF EXISTS `wim_nfvo_tenants`;
CREATE TABLE `wim_nfvo_tenants` (
  `id` integer NOT NULL AUTO_INCREMENT,
  `nfvo_tenant_id` varchar(36) NOT NULL,
  `wim_id` varchar(36) NOT NULL,
  `wim_account_id` varchar(36) NOT NULL,
  `created_at` double NOT NULL,
  `modified_at` double DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `wim_nfvo_tenant` (`wim_id`,`nfvo_tenant_id`),
  KEY `FK_wims_nfvo_tenants` (`wim_id`),
  KEY `FK_wim_accounts_nfvo_tenants` (`wim_account_id`),
  KEY `FK_nfvo_tenants_wim_accounts` (`nfvo_tenant_id`),
  CONSTRAINT `FK_wims_nfvo_tenants` FOREIGN KEY (`wim_id`)
    REFERENCES `wims` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_wim_accounts_nfvo_tenants` FOREIGN KEY (`wim_account_id`)
    REFERENCES `wim_accounts` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_nfvo_tenants_wim_accounts` FOREIGN KEY (`nfvo_tenant_id`)
    REFERENCES `nfvo_tenants` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
)
ENGINE=InnoDB AUTO_INCREMENT=86 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT
COMMENT='WIM accounts mapping to NFVO tenants';

DROP TABLE IF EXISTS `instance_wim_nets`;
CREATE TABLE `instance_wim_nets` (
  `uuid` varchar(36) NOT NULL,
  `wim_internal_id` varchar(128) DEFAULT NULL
    COMMENT 'Internal ID used by the WIM to refer to the network',
  `instance_scenario_id` varchar(36) DEFAULT NULL,
  `sce_net_id` varchar(36) DEFAULT NULL,
  `wim_id` varchar(36) DEFAULT NULL,
  `wim_account_id` varchar(36) NOT NULL,
  `status` enum(
    'ACTIVE',
    'INACTIVE',
    'DOWN',
    'BUILD',
    'ERROR',
    'WIM_ERROR',
    'DELETED',
    'SCHEDULED_CREATION',
    'SCHEDULED_DELETION') NOT NULL DEFAULT 'BUILD',
  `error_msg` varchar(1024) DEFAULT NULL,
  `wim_info` text,
  `multipoint` enum('true','false') NOT NULL DEFAULT 'false',
  `created` enum('true','false') NOT NULL DEFAULT 'false'
      COMMENT 'Created or already exists at WIM',
  `created_at` double NOT NULL,
  `modified_at` double DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  KEY `FK_instance_wim_nets_instance_scenarios` (`instance_scenario_id`),
  KEY `FK_instance_wim_nets_sce_nets` (`sce_net_id`),
  KEY `FK_instance_wim_nets_wims` (`wim_id`),
  KEY `FK_instance_wim_nets_wim_accounts` (`wim_account_id`),
  CONSTRAINT `FK_instance_wim_nets_wim_accounts`
    FOREIGN KEY (`wim_account_id`) REFERENCES `wim_accounts` (`uuid`),
  CONSTRAINT `FK_instance_wim_nets_wims`
    FOREIGN KEY (`wim_id`) REFERENCES `wims` (`uuid`),
  CONSTRAINT `FK_instance_wim_nets_instance_scenarios`
    FOREIGN KEY (`instance_scenario_id`) REFERENCES `instance_scenarios` (`uuid`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_instance_wim_nets_sce_nets`
    FOREIGN KEY (`sce_net_id`) REFERENCES `sce_nets` (`uuid`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT
  COMMENT='Instances of wim networks';

ALTER TABLE `vim_actions`
  RENAME TO `vim_wim_actions`;
ALTER TABLE `vim_wim_actions`
  ADD `wim_account_id` varchar(36) DEFAULT NULL AFTER `vim_id`,
  ADD `wim_internal_id` varchar(64) DEFAULT NULL AFTER `wim_account_id`,
  MODIFY `datacenter_vim_id` varchar(36) DEFAULT NULL,
  MODIFY `item` enum(
    'datacenters_flavors',
    'datacenter_images',
    'instance_nets',
    'instance_vms',
    'instance_interfaces',
    'instance_wim_nets') NOT NULL
  COMMENT 'table where the item is stored';
ALTER TABLE `vim_wim_actions`
  ADD INDEX `item_type_id` (`item`, `item_id`);
ALTER TABLE `vim_wim_actions`
  ADD INDEX `FK_actions_wims` (`wim_account_id`);
ALTER TABLE `vim_wim_actions`
  ADD CONSTRAINT `FK_actions_wims` FOREIGN KEY (`wim_account_id`)
  REFERENCES `wim_accounts` (`uuid`)
  ON UPDATE CASCADE ON DELETE CASCADE;

DROP TABLE IF EXISTS `wim_port_mappings`;
CREATE TABLE `wim_port_mappings` (
  `id` integer NOT NULL AUTO_INCREMENT,
  `wim_id` varchar(36) NOT NULL,
  `datacenter_id` varchar(36) NOT NULL,
  `pop_switch_dpid` varchar(64) NOT NULL,
  `pop_switch_port` varchar(64) NOT NULL,
  `wan_service_endpoint_id` varchar(256) NOT NULL
      COMMENT 'In case the WIM plugin relies on the wan_service_mapping_info'
      COMMENT 'this field contains a unique identifier used to check the mapping_info consistency',
      /* In other words: wan_service_endpoint_id = f(wan_service_mapping_info)
       * where f is a injective function'
       */
  `wan_service_mapping_info` text,
  `created_at` double NOT NULL,
  `modified_at` double DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_datacenter_port_mapping`
    (`datacenter_id`, `pop_switch_dpid`, `pop_switch_port`),
  UNIQUE KEY `unique_wim_port_mapping`
    (`wim_id`, `wan_service_endpoint_id`),
  KEY `FK_wims_wim_physical_connections` (`wim_id`),
  KEY `FK_datacenters_wim_port_mappings` (`datacenter_id`),
  CONSTRAINT `FK_wims_wim_port_mappings` FOREIGN KEY (`wim_id`)
    REFERENCES `wims` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_datacenters_wim_port_mappings` FOREIGN KEY (`datacenter_id`)
    REFERENCES `datacenters` (`uuid`) ON DELETE CASCADE ON UPDATE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8
COMMENT='WIM port mappings managed by the WIM.';

-- Update Schema with DB version
INSERT INTO schema_version
VALUES (34, '0.34', '0.6.00', 'Added WIM tables', '2018-09-10');
