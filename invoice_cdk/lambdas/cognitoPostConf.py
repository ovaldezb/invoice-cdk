import boto3

def handler(event, context):
    print(event)
    client = boto3.client("cognito-idp")
    user_name = event['userName']
    user_pool_id = event['userPoolId']
    grupo = event['request']['userAttributes']['custom:group']
    client.admin_add_user_to_group(
        UserPoolId=user_pool_id,
        Username=user_name,
        GroupName=grupo
    )
    return event
    