import pytest
from integrations.formatters import FormatterFactory, BaseFormatter, SlackFormatter, JiraFormatter, SplunkFormatter

def test_formatter_factory():
    assert FormatterFactory.get_formatter('GENERIC') == BaseFormatter
    assert FormatterFactory.get_formatter('SLACK') == SlackFormatter
    assert FormatterFactory.get_formatter('JIRA') == JiraFormatter
    assert FormatterFactory.get_formatter('SPLUNK') == SplunkFormatter
    assert FormatterFactory.get_formatter('UNKNOWN') == BaseFormatter

def test_slack_formatter():
    payload = {
        "scan_id": "123",
        "target_host": "example.com",
        "scan_status": "completed",
        "critical_count": 1,
        "high_count": 0,
        "medium_count": 2,
        "low_count": 0
    }
    config = {}
    
    result = SlackFormatter.format(payload, "scan.completed", config)
    
    assert "blocks" in result
    blocks = result["blocks"]
    assert len(blocks) == 3
    assert blocks[0]["text"]["text"] == "HackerScan Alert: Scan COMPLETED"
    
    counts_block = blocks[2]
    assert "*Critical:* 1" in counts_block["fields"][0]["text"]
    assert "*High:* 0" in counts_block["fields"][1]["text"]

def test_jira_formatter():
    payload = {
        "scan_id": "123",
        "target_host": "example.com",
        "scan_status": "completed",
        "critical_count": 1
    }
    config = {"project_key": "SEC"}
    
    result = JiraFormatter.format(payload, "scan.completed", config)
    
    assert result["fields"]["project"]["key"] == "SEC"
    assert result["fields"]["summary"] == "[HackerScan] Scan completed on example.com"
    assert "*scan_id*: 123" in result["fields"]["description"]
    assert result["fields"]["issuetype"]["name"] == "Task"

def test_splunk_formatter():
    payload = {"data": "test"}
    config = {"source": "my-app", "sourcetype": "_json"}
    
    result = SplunkFormatter.format(payload, "scan.completed", config)
    
    assert result["source"] == "my-app"
    assert result["sourcetype"] == "_json"
    assert result["event"] == payload
