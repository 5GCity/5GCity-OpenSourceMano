class AlarmConfig:
    def __init__(self, metric_name, resource_uuid, vim_uuid, threshold, operation, statistic, action):
        self.metric_name = metric_name,
        self.resource_uuid = resource_uuid,
        self.vim_uuid = vim_uuid,
        self.threshold = threshold,
        self.operation = operation,
        self.statistic = statistic,
        self.action = action
