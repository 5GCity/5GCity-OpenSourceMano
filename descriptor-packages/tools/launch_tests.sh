#!/usr/bin/env bash

function test_format
{
 folder=$(dir -1)

 for file in $folder;
 do
  if [ -n $file ]; then
       if [ -d "$file" ]; then

            cd $file
            test_format
            cd ..
       else
            extension=${file##*.}
            name=${file%.*}
            folder_file=`pwd`
            if [ $extension == "yaml" ]; then
                $tools_dir/upgrade_descriptor_version.py --test -i $folder_file"/"$name.$extension -o $folder_file"/"$name."output" 2> $folder_file"/"$name."error"
                [ -s $folder_file"/"$name."output" ] || rm $folder_file"/"$name."output"
                [ -s $folder_file"/"$name."error" ] || rm $folder_file"/"$name."error"
            fi;
       fi;
  fi;
 done;
}


top_dir=`readlink -f .|sed -e 's/\/descriptor-packages\/.*//'`
tools_dir=${top_dir}/tools

if [ -f $tools_dir/upgrade_descriptor_version.py ]; then
    cd ${top_dir}/
    test_format ./
else
    print "Error: 'make' command should be called inside '/devops/descriptor-packages/' folder to work"
    exit -1
fi;
