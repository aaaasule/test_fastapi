            _interface_field_prefixes = ('ID.', 'CS.', 'CT.')
            fields_to_remove = []
            for field_item in final_results['field']:
                all_errors = field_item.get('errors') or []
                interface_required_errors = [
                    e for e in all_errors
                    if e.get('errorName') == '必填项缺失'
                    and any(prefix in e.get('errorDescription', '') for prefix in _interface_field_prefixes)
                ]
                if not interface_required_errors:
                    continue

                all_migrated = len(interface_required_errors) == len(all_errors)

                matched = False
                for interface_item in final_results['interfaces']:
                    if interface_item.get('cadBlockId') == field_item.get('cadBlockId'):
                        if interface_item.get('errors') is None:
                            interface_item['errors'] = []
                        interface_item['errors'].extend(interface_required_errors)
                        matched = True
                if not matched:
                    new_interface = {
                        'id': None,
                        'parent_id': '',
                        'field_id': field_item.get('id'),
                        'fab_id': field_item.get('fab_id'),
                        'building_id': field_item.get('building_id'),
                        'building_level': field_item.get('building_level'),
                        'uniCode': field_item.get('searchId'),
                        'code': field_item.get('code'),
                        'field_code': field_item.get('uniCode'),
                        'searchId': field_item.get('searchId'),
                        'conSize': field_item.get('conSize'),
                        'conType': field_item.get('conType'),
                        'maxDesignFlow': field_item.get('maxDesignFlow'),
                        'unit': field_item.get('unit'),
                        'is_Assigned': None,
                        'chemicalName': field_item.get('chemicalName'),
                        'isOutCode': None,
                        'locked': field_item.get('locked'),
                        'layer': field_item.get('layer'),
                        'insertPointX': field_item.get('insertPointX'),
                        'insertPointY': field_item.get('insertPointY'),
                        'insertPointZ': field_item.get('insertPointZ'),
                        'angle': field_item.get('angle'),
                        'trueColor': field_item.get('trueColor'),
                        'cadBlockId': field_item.get('cadBlockId'),
                        'cadBlockName': field_item.get('cadBlockName'),
                        'distributionBox': field_item.get('distributionBox'),
                        'errors': interface_required_errors
                    }
                    final_results['interfaces'].append(new_interface)

                if all_migrated:
                    fields_to_remove.append(field_item)
                else:
                    field_item['errors'] = [
                        e for e in all_errors
                        if not (
                            e.get('errorName') == '必填项缺失'
                            and any(prefix in e.get('errorDescription', '') for prefix in _interface_field_prefixes)
                        )
                    ]
            for _f in fields_to_remove:
                final_results['field'].remove(_f)
