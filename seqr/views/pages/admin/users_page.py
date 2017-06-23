from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.http.response import HttpResponse
from django.template.base import Template
from django.template.context import RequestContext

TEMPLATE = Template("""
<html>
<head>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
    <script type="text/javascript" charset="utf8" src="//cdn.datatables.net/1.10.13/js/jquery.dataTables.js"></script>
    <link rel="stylesheet" type="text/css" href="//cdn.datatables.net/1.10.13/css/jquery.dataTables.css">

    <script>
    $(document).ready(function(){
        var t = $('#userTable').DataTable({
            paging: false,
            columnDefs: [ {
                searchable: false,
                orderable: false,
                targets: 0,
            } ],

            order: [[ 1, 'asc' ]]
        });

        // index column (https://datatables.net/examples/api/counter_columns.html)
        t.on( 'order.dt search.dt', function () {
            t.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
                cell.innerHTML = i+1;
            } );
        } ).draw();
    });
    </script>
    <style>
        .nowrap {
            white-space: nowrap
        }
    </style>
</head>
<body>
    <a href="/">seqr</a>  &nbsp; <a href="/dashboard">dashboard</a>
    <table id="userTable" class="display">
    <thead>
        <tr>
            <th> </th>
            <th width="80%">email</th>
            <th class="nowrap">username</th>
            <th class="nowrap" data-s-type="date">date joined</th>
            <th class="nowrap" data-s-type="date">last login</th>
            <th class="nowrap">name</th>
            <th class="nowrap">staff</th>
            <th class="nowrap">superuser</th>
            <th class="nowrap">id</th>
            <th class="nowrap">login as</th>
        </tr>
    </thead>
    {% for user in users %}
        <tr>
            <td> </td>
            <td>{{ user.email }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.date_joined|date:'Y-m-d' }}</td>
            <td>{{ user.last_login|date:'Y-m-d' }}</td>
            <td>{{ user.first_name }} {{ user.last_name }}</td>
            <td>{% if user.is_staff %} &#x2714; {% endif %}</td>
            <td>{% if user.is_superuser %} &#x2714; {% endif %}</td>
            <td>{{ user.id }}</td>
            <td>
                <form action="/hijack/{{ user.id }}/" method="post">
                    {% csrf_token %}
                    <button type="submit">Log in</button>
                </form>
            </td>
        </tr>
    {% endfor %}
    </table>
</body>
</html>
""")


@staff_member_required
def users_template(request):
    # generate HttpResponse. Use RequestContext instead of Context so that csrf_token is handled properly
    c = RequestContext(request, {
        'users': User.objects.all().order_by('email')
    })

    return HttpResponse(TEMPLATE.render(c))
