"""Optional public-demo analysis allowance. No document content is stored."""
import os

def consume(client=None):
    table=os.environ.get('CAPTUREGATE_ALLOWANCE_TABLE')
    if not table:
        return None  # Existing local/private configuration remains unchanged.
    try:
        limit=int(os.environ.get('CAPTUREGATE_ANALYSIS_LIMIT','1000'))
        if not 1 <= limit <= 1000:
            raise ValueError('Invalid allowance')
        if client is None:
            import boto3
            client=boto3.client('dynamodb')
        client.update_item(
            TableName=table,Key={'id':{'S':'analysis'}},
            UpdateExpression='SET used = if_not_exists(used, :zero) + :one',
            ConditionExpression='attribute_not_exists(used) OR used < :limit',
            ExpressionAttributeValues={':zero':{'N':'0'},':one':{'N':'1'},':limit':{'N':str(limit)}})
        return None
    except Exception as exc:
        if getattr(exc,'response',{}).get('Error',{}).get('Code')=='ConditionalCheckFailedException':
            return 429,'Public demo allowance reached. Use the local version or contact the presenter.'
        return 503,'Public demo allowance check unavailable. Analysis is paused; try again later.'
